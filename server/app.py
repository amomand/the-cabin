"""FastAPI WebSocket server for The Cabin."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import time
from pathlib import Path

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

# Load .env before any other game import. game.env pulls in nothing else from
# the package, so this really does run first (issue #178).
from game.env import load_game_dotenv

load_game_dotenv()

from server.session import WebGameSession
from server.rate_limiter import RateLimiter
from server.protocol import (
    BROKEN_MESSAGE_TEXT,
    UNKNOWN_MESSAGE_TEXT,
    decode_turn_message,
)
from server.session_store import (
    IdentityBusy,
    SessionStore,
    StoredSession,
    is_valid_client_id,
    prune_expired_saves,
)

logger = logging.getLogger("the-cabin")

CONNECTION_REFUSED_TEXT = "The room refuses another voice."
SESSION_TIMEOUT_TEXT = "The thread goes cold. The room lets you go."
RATE_LIMIT_TEXT = "The room needs a moment to settle."
ORIGIN_REFUSED_TEXT = "The room does not answer that door."
UNKNOWN_SESSION_TEXT = "That thread has gone cold. The room remembers nothing of it."
UNKNOWN_IDENTITY_TEXT = "The room will not answer to that name."
IDENTITY_BUSY_TEXT = "The room is still holding your last breath. Wait."
TURN_FAILED_TEXT = "The thread breaks. The room lets you go."

# Header set by the Fly edge with the real client address. Trusted over the
# client-controlled X-Forwarded-For, whose left-most value is spoofable.
TRUSTED_CLIENT_IP_HEADER = "fly-client-ip"

# WebSocket Origin allowlist (CSWSH protection). Overridable via env so the
# deployed front-end origin can change without a code change.
DEFAULT_ALLOWED_ORIGINS = (
    "https://www.the-cabin.fi",
    "https://the-cabin.fi",
    "https://the-cabin-api.fly.dev",
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


def _release_session_slot(stored: StoredSession) -> None:
    """Give back the connection slot a stored session was holding.

    Looked up through the module global so tests that swap in a fresh limiter
    still see their own instance.
    """
    rate_limiter.release_connection(stored.ip)


session_store = SessionStore(
    idle_timeout=rate_limiter.session_timeout,
    on_release=_release_session_slot,
)

# Durable save pruning walks the filesystem, so it runs on a timer rather than
# on every session creation.
SAVE_PRUNE_INTERVAL_SECONDS = 3600.0
_last_save_prune: float = 0.0


def _sweep_sessions() -> None:
    """Expire idle HTTP sessions, keeping the store's timeout in step."""
    session_store.idle_timeout = rate_limiter.session_timeout
    # Tokens are bearer secrets, so nothing identifying goes to the log.
    for _ in session_store.sweep():
        logger.info("HTTP session expired (sessions: %d)", rate_limiter.active_sessions)


def _maybe_prune_saves() -> None:
    global _last_save_prune
    now = time.monotonic()
    if _last_save_prune and now - _last_save_prune < SAVE_PRUNE_INTERVAL_SECONDS:
        return
    _last_save_prune = now
    for path in prune_expired_saves(session_store.live_save_dirs()):
        logger.info("Pruned stale save dir: %s", path)


def _error(status: int, text: str) -> JSONResponse:
    """Error responses carry a narrated line, never bare framework text."""
    return JSONResponse(status_code=status, content={"type": "error", "message": text})


def _client_ip(ws: WebSocket | Request) -> str:
    """Best-effort client IP for rate limiting.

    Works for both surfaces: ``WebSocket`` and ``Request`` expose the same
    ``headers`` and ``client`` attributes, so the WS and HTTP paths share one
    set of trust rules.

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


def _origin_allowed(ws: WebSocket | Request) -> bool:
    """Allow requests with no Origin (non-browser clients) or an allowed one.

    A native client sends no Origin, so it is unaffected. A hostile page always
    sends one, which is what makes this worth checking on both surfaces: on
    `/ws` it stops cross-site WebSocket hijacking, and on the HTTP endpoints it
    stops a drive-by page opening sessions and spending model credit.
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
    _sweep_sessions()
    return {
        "status": "ok",
        "active_sessions": rate_limiter.active_sessions,
    }


# -- HTTP session API -------------------------------------------------------
#
# A native client cannot hold a socket open: iOS suspends a backgrounded app
# and kills its connections, so a WebSocket run ends at the first phone lock.
# The protocol is strictly request -> response, so these endpoints carry the
# same turns over plain HTTP with no reconnect problem to solve.
#
# The token travels in an ``Authorization: Bearer`` header rather than the URL,
# so it stays out of access and proxy logs. It is not an ambient credential
# like a cookie, so no cross-site request can ride along on it; the Origin
# check below exists to stop a hostile page opening sessions in the first
# place, not to protect an existing one.

# Turn bodies carry at most a short line of player input, so anything larger is
# refused before it is buffered.
MAX_BODY_BYTES = 8 * 1024

# Sentinels distinguishing an oversized body from an unparseable one.
_TOO_LARGE = object()
_UNPARSEABLE = object()


async def _read_capped_body(request: Request) -> bytes | None:
    """Read the request body, or None if it exceeds ``MAX_BODY_BYTES``.

    The declared length is only a hint (a chunked request has none), so the
    stream is measured as it arrives rather than trusted up front.
    """
    declared = request.headers.get("content-length")
    if declared is not None:
        try:
            if int(declared) > MAX_BODY_BYTES:
                return None
        except ValueError:
            return None

    chunks: list[bytes] = []
    size = 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > MAX_BODY_BYTES:
            return None
        chunks.append(chunk)
    return b"".join(chunks)


async def _json_body(request: Request) -> object:
    """Parse a JSON body, treating an empty one as an empty message.

    Returns ``_TOO_LARGE`` for an oversized body and ``_UNPARSEABLE`` for one
    that is not JSON at all. Anything else is handed on as parsed, for
    ``decode_turn_message`` to judge.
    """
    raw = await _read_capped_body(request)
    if raw is None:
        return _TOO_LARGE
    if not raw.strip():
        return {}
    try:
        return json.loads(raw)
    except (ValueError, UnicodeDecodeError):
        # ValueError covers JSONDecodeError and the bare ValueError CPython
        # raises for an integer past its digit limit, which fits well inside
        # the body cap and would otherwise surface as a framework 500.
        return _UNPARSEABLE


def _bearer_token(request: Request) -> str | None:
    """Extract the session token from an ``Authorization: Bearer`` header."""
    header = request.headers.get("authorization")
    if not header:
        return None
    scheme, _, value = header.partition(" ")
    if scheme.lower() != "bearer":
        return None
    token = value.strip()
    return token or None


@app.post("/session")
async def create_session(request: Request):
    """Start a run and return its token plus the intro frame."""
    _sweep_sessions()

    if not _origin_allowed(request):
        return _error(403, ORIGIN_REFUSED_TEXT)

    ip = _client_ip(request)

    # Reserve the slot in the same breath as the check. Anything awaited
    # between the two lets concurrent creates all pass a stale check and
    # overshoot the cap. Rollback returns the slot but keeps the attempt's
    # timestamp, so a burst of malformed bodies still counts against the
    # per-minute limit rather than being free.
    if not rate_limiter.can_connect(ip):
        return _error(429, CONNECTION_REFUSED_TEXT)
    rate_limiter.register_connection(ip)

    stored = None
    try:
        body = await _json_body(request)
        if body is _TOO_LARGE:
            return _error(413, BROKEN_MESSAGE_TEXT)
        if body is _UNPARSEABLE or not isinstance(body, dict):
            return _error(400, BROKEN_MESSAGE_TEXT)

        client_id = body.get("client_id")
        if client_id is not None:
            if not isinstance(client_id, str) or not is_valid_client_id(client_id):
                return _error(400, UNKNOWN_IDENTITY_TEXT)

        try:
            stored = session_store.create(ip=ip, client_id=client_id)
        except IdentityBusy:
            return _error(409, IDENTITY_BUSY_TEXT)
        except Exception:
            logger.exception("Failed to open HTTP session for %s", ip)
            return _error(500, TURN_FAILED_TEXT)

        # Prune only once this session exists, so its own directory counts as
        # live. Pruning first would let a player returning right on the
        # retention boundary watch their history deleted a moment before they
        # could load it.
        _maybe_prune_saves()
    finally:
        # Any path that did not end up with a stored session must hand the
        # slot back; nothing else would, because nothing was stored.
        if stored is None:
            rate_limiter.release_connection(ip)

    logger.info(
        "HTTP session opened: %s (sessions: %d)", ip, rate_limiter.active_sessions
    )

    return {
        "token": stored.token,
        "frame": stored.session.get_intro_frame().to_dict(),
    }


@app.post("/session/turn")
async def session_turn(request: Request):
    """Play one turn against an existing session and return the next frame."""
    _sweep_sessions()

    if not _origin_allowed(request):
        return _error(403, ORIGIN_REFUSED_TEXT)

    ip = _client_ip(request)

    # Rate limit before the token lookup so probing for live tokens costs the
    # same budget as playing, rather than being free.
    if not rate_limiter.can_send_message(ip):
        return _error(429, RATE_LIMIT_TEXT)
    rate_limiter.register_message(ip)

    token = _bearer_token(request)
    stored = session_store.get(token) if token else None
    if stored is None:
        terminal = session_store.terminal_replay(token) if token else None
        if terminal is None:
            return _error(404, UNKNOWN_SESSION_TEXT)

        body = await _json_body(request)
        if body is _TOO_LARGE:
            return _error(413, BROKEN_MESSAGE_TEXT)
        if body is _UNPARSEABLE:
            return _error(400, BROKEN_MESSAGE_TEXT)
        text, message_error = decode_turn_message(body)
        if message_error is not None:
            return _error(400, message_error)
        turn_type = body.get("type") if isinstance(body, dict) else None
        turn_id = body.get("turn_id") if isinstance(body, dict) else None
        if (
            turn_id != terminal.turn_id
            or turn_type != terminal.turn_type
            or text != terminal.text
        ):
            return _error(400, BROKEN_MESSAGE_TEXT)
        return terminal.frame

    # Arrival counts as activity, as it does on the WS path. The in-flight
    # count holds off expiry for as long as this request lives, so a sweep
    # cannot release the session, or delete its save directory, mid-turn.
    stored.touch()
    stored.in_flight += 1
    try:
        body = await _json_body(request)
        if body is _TOO_LARGE:
            return _error(413, BROKEN_MESSAGE_TEXT)
        if body is _UNPARSEABLE:
            return _error(400, BROKEN_MESSAGE_TEXT)

        text, message_error = decode_turn_message(body)
        if message_error is not None:
            return _error(400, message_error)

        turn_type = body.get("type") if isinstance(body, dict) else None
        turn_id = body.get("turn_id") if isinstance(body, dict) else None
        if turn_id is not None and (
            isinstance(turn_id, bool) or not isinstance(turn_id, int) or turn_id < 1
        ):
            return _error(400, BROKEN_MESSAGE_TEXT)

        err = rate_limiter.validate_input(text)
        if err:
            return _error(400, err)

        # One turn at a time per session: a double-tapped send must not run two
        # turns against the same mutable game state concurrently. The turn
        # itself runs in a thread for the same reason as the WS path (see
        # below).
        async with stored.lock:
            # A session retired while this request waited for the lock (a new
            # run from the same identity, say) must not be resurrected by it.
            if session_store.get(stored.token) is not stored:
                terminal = session_store.terminal_replay(stored.token)
                if (
                    terminal is not None
                    and turn_id == terminal.turn_id
                    and turn_type == terminal.turn_type
                    and text == terminal.text
                ):
                    return terminal.frame
                return _error(404, UNKNOWN_SESSION_TEXT)

            if turn_id is not None and stored.last_turn_id is not None:
                if turn_id == stored.last_turn_id:
                    if (
                        turn_type != stored.last_turn_type
                        or text != stored.last_turn_text
                    ):
                        return _error(400, BROKEN_MESSAGE_TEXT)
                    # The first request may still have been running when its
                    # retry arrived. Waiting for the lock puts us here only
                    # after its exact frame has been cached.
                    return stored.last_turn_frame
                if turn_id != stored.last_turn_id + 1:
                    return _error(400, BROKEN_MESSAGE_TEXT)
            elif turn_id is not None and turn_id != 1:
                return _error(400, BROKEN_MESSAGE_TEXT)

            loop = asyncio.get_running_loop()
            try:
                frame = await loop.run_in_executor(
                    None, stored.session.handle_input, text
                )
            except Exception:
                # The WS path releases the session on a failed turn; do the
                # same here rather than leaving a wedged one holding a slot.
                logger.exception("HTTP turn failed for %s", ip)
                session_store.release(stored.token)
                return _error(500, TURN_FAILED_TEXT)
            stored.touch()
            if turn_id is not None:
                stored.last_turn_id = turn_id
                stored.last_turn_type = turn_type
                stored.last_turn_text = text
                stored.last_turn_frame = frame.to_dict()
    finally:
        stored.in_flight -= 1

    if frame.game_over:
        session_store.release(
            stored.token,
            preserve_terminal_replay=turn_id is not None,
        )

    return frame.to_dict()


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

            # Parse client message. Decoding is shared with the HTTP surface
            # so an odd payload gets the same answer on both.
            try:
                msg = json.loads(raw)
            except ValueError:
                # Covers JSONDecodeError plus the bare ValueError CPython
                # raises for an over-long integer, which would otherwise
                # escape the loop and kill the socket.
                await ws.send_json({
                    "type": "error",
                    "message": BROKEN_MESSAGE_TEXT,
                })
                continue

            text, message_error = decode_turn_message(msg)
            if message_error is not None:
                await ws.send_json({"type": "error", "message": message_error})
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


def _mount_site(target_app: FastAPI) -> None:
    """Serve the static site from the same app as the WebSocket API.

    The site directory is baked into the Docker image (see Dockerfile); when
    it is absent — local dev, tests, or an API-only deploy — the app simply
    serves /health and /ws as before. Mounted last, so the API routes defined
    above always win.
    """
    site_dir = Path(os.getenv("CABIN_SITE_DIR", "site"))
    if site_dir.is_dir():
        target_app.mount("/", StaticFiles(directory=site_dir, html=True), name="site")


_mount_site(app)
