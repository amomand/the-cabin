"""FastAPI WebSocket server for The Cabin."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import time

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from server.session import WebGameSession
from server.rate_limiter import RateLimiter

logger = logging.getLogger("the-cabin")

CONNECTION_REFUSED_TEXT = "The room refuses another voice."
SESSION_TIMEOUT_TEXT = "The thread goes cold. The room lets you go."
BROKEN_MESSAGE_TEXT = "The words arrive broken. The room gives them nothing."
UNKNOWN_MESSAGE_TEXT = "The words find no shape here."
RATE_LIMIT_TEXT = "The room needs a moment to settle."
ORIGIN_REFUSED_TEXT = "The room does not answer that door."

# Header set by the Fly edge with the real client address. Trusted over the
# client-controlled X-Forwarded-For, whose left-most value is spoofable.
TRUSTED_CLIENT_IP_HEADER = "fly-client-ip"

# WebSocket Origin allowlist (CSWSH protection). Overridable via env so the
# deployed front-end origin can change without a code change.
DEFAULT_ALLOWED_ORIGINS = (
    "https://www.the-cabin.fi",
    "https://the-cabin.fi",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
)

app = FastAPI(title="The Cabin", docs_url=None, redoc_url=None)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

rate_limiter = RateLimiter()


def _client_ip(ws: WebSocket) -> str:
    """Best-effort client IP for rate limiting.

    Trust the platform-set header (Fly sets ``Fly-Client-IP``) over the
    client-controlled ``X-Forwarded-For``. A left-most XFF value is spoofable
    and must never drive per-IP limits; only fall back to it as a last resort,
    taking the right-most (closest, least attacker-controlled) hop.
    """
    trusted = ws.headers.get(TRUSTED_CLIENT_IP_HEADER)
    if trusted:
        return trusted.strip()
    if ws.client:
        return ws.client.host
    forwarded = ws.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[-1].strip()
    return "unknown"


def _allowed_origins() -> set[str]:
    """Return the WebSocket Origin allowlist, from env or the defaults."""
    raw = os.getenv("CABIN_ALLOWED_ORIGINS")
    if raw:
        return {o.strip() for o in raw.split(",") if o.strip()}
    return set(DEFAULT_ALLOWED_ORIGINS)


def _origin_allowed(ws: WebSocket) -> bool:
    """Allow connections with no Origin (non-browser clients) or an allowed one.

    Cross-site WebSocket hijacking always carries a browser-set Origin, so a
    present-but-unlisted Origin is the case to reject.
    """
    origin = ws.headers.get("origin")
    if origin is None:
        return True
    return origin in _allowed_origins()


def _cleanup_session_saves(session: WebGameSession) -> None:
    """Remove a web session's throwaway save directory, if it was created.

    Runs in the connection ``finally`` block, so it must never raise.
    """
    save_manager = getattr(session, "save_manager", None)
    save_dir = getattr(save_manager, "save_dir", None)
    if save_dir is None:
        return
    try:
        if save_dir.exists():
            shutil.rmtree(save_dir, ignore_errors=True)
    except OSError:
        logger.debug("Failed to clean session save dir: %s", save_dir, exc_info=True)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "active_sessions": rate_limiter.active_sessions,
    }


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    ip = _client_ip(ws)

    if not _origin_allowed(ws):
        await ws.close(code=1008, reason=ORIGIN_REFUSED_TEXT)
        return

    if not rate_limiter.can_connect(ip):
        await ws.close(code=1008, reason=CONNECTION_REFUSED_TEXT)
        return

    await ws.accept()
    rate_limiter.register_connection(ip)
    logger.info("WS connected: %s (sessions: %d)", ip, rate_limiter.active_sessions)

    session = WebGameSession()
    last_activity = time.monotonic()

    try:
        # Send intro frame
        intro = session.get_intro_frame()
        await ws.send_json(intro.to_dict())

        while True:
            # Check idle timeout
            if time.monotonic() - last_activity > rate_limiter.session_timeout:
                await ws.send_json({
                    "type": "error",
                    "message": SESSION_TIMEOUT_TEXT,
                })
                break

            try:
                raw = await asyncio.wait_for(ws.receive_text(), timeout=60.0)
            except asyncio.TimeoutError:
                continue  # No message — loop back and recheck idle timeout

            last_activity = time.monotonic()

            # Parse client message
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await ws.send_json({
                    "type": "error",
                    "message": BROKEN_MESSAGE_TEXT,
                })
                continue

            msg_type = msg.get("type")

            if msg_type == "keypress":
                text = ""
            elif msg_type == "input":
                text = msg.get("text", "")
            else:
                await ws.send_json({
                    "type": "error",
                    "message": UNKNOWN_MESSAGE_TEXT,
                })
                continue

            # Rate limit messages
            if not rate_limiter.can_send_message(ip):
                await ws.send_json({
                    "type": "error",
                    "message": RATE_LIMIT_TEXT,
                })
                continue
            rate_limiter.register_message(ip)

            # Validate input length
            if msg_type == "input":
                err = rate_limiter.validate_input(text)
                if err:
                    await ws.send_json({"type": "error", "message": err})
                    continue

            # Run the (potentially blocking) game logic in a thread. A single
            # turn is bounded by the OpenAI client timeout (see ai_interpreter):
            # on a slow or stuck model call interpret() raises and falls back to
            # rule-based parsing, so handle_input returns promptly. We deliberately
            # do not wrap this in an asyncio per-turn deadline, because wait_for()
            # cannot cancel the worker thread; abandoning it mid-turn would let it
            # keep mutating session state after the connection has moved on.
            loop = asyncio.get_running_loop()
            frame = await loop.run_in_executor(None, session.handle_input, text)

            await ws.send_json(frame.to_dict())

            if frame.game_over:
                break

    except WebSocketDisconnect:
        logger.info("WS disconnected: %s", ip)
    except Exception:
        logger.exception("WS error for %s", ip)
    finally:
        rate_limiter.release_connection(ip)
        _cleanup_session_saves(session)
        logger.info("WS cleanup: %s (sessions: %d)", ip, rate_limiter.active_sessions)
