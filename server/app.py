"""FastAPI WebSocket server for The Cabin."""

from __future__ import annotations

import asyncio
import json
import logging
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

app = FastAPI(title="The Cabin", docs_url=None, redoc_url=None)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

rate_limiter = RateLimiter()


def _client_ip(ws: WebSocket) -> str:
    """Best-effort client IP (respects X-Forwarded-For behind proxy)."""
    forwarded = ws.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if ws.client:
        return ws.client.host
    return "unknown"


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "active_sessions": rate_limiter.active_sessions,
    }


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    ip = _client_ip(ws)

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

            # Run the (potentially blocking) game logic in a thread
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
        logger.info("WS cleanup: %s (sessions: %d)", ip, rate_limiter.active_sessions)
