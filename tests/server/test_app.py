"""Tests for the deployed FastAPI/WebSocket entrypoint (server.app).

These exercise the WebSocket endpoint end-to-end through Starlette's TestClient,
with no OpenAI key required — WebGameSession falls back to rule-based parsing.
Each test swaps in a freshly configured RateLimiter so connection/message limits
and idle timeouts can be driven deterministically.
"""

import pytest
from types import SimpleNamespace

from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

import server.app as app_module
from server.app import (
    app,
    BROKEN_MESSAGE_TEXT,
    UNKNOWN_MESSAGE_TEXT,
    RATE_LIMIT_TEXT,
    SESSION_TIMEOUT_TEXT,
)
from server.rate_limiter import RateLimiter
from server.session import WebGameSession
from game.ai_interpreter import clear_response_cache


@pytest.fixture(autouse=True)
def _clear_ai_cache():
    clear_response_cache()
    yield
    clear_response_cache()


@pytest.fixture
def limiter(monkeypatch):
    """Install a fresh RateLimiter and return a setter for per-test config."""
    def install(**kwargs):
        rl = RateLimiter(**kwargs)
        monkeypatch.setattr(app_module, "rate_limiter", rl)
        return rl
    return install


@pytest.fixture
def client():
    return TestClient(app)


def _intro(ws) -> dict:
    """Receive and return the intro frame the server sends on connect."""
    return ws.receive_json()


class TestHealth:
    def test_health_reports_active_sessions(self, client, limiter):
        limiter()
        resp = client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert body["active_sessions"] == 0


class TestConnection:
    def test_intro_frame_sent_on_connect(self, client, limiter):
        limiter()
        with client.websocket_connect("/ws") as ws:
            intro = _intro(ws)
            assert intro["type"] == "render"
            assert "You shouldn't have come back." in intro["lines"]
            assert intro["wait_for_key"] is True

    def test_connection_refused_when_at_capacity(self, client, limiter):
        limiter(max_sessions=0)
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect("/ws") as ws:
                _intro(ws)

    def test_keypress_dismisses_intro_and_renders_room(self, client, limiter):
        limiter()
        with client.websocket_connect("/ws") as ws:
            _intro(ws)
            ws.send_json({"type": "keypress"})
            frame = ws.receive_json()
            assert frame["type"] == "render"
            assert any("Wilderness" in line for line in frame["lines"])
            assert frame["prompt"] == "> "


class TestMessageHandling:
    def test_malformed_json_returns_broken_message(self, client, limiter):
        limiter()
        with client.websocket_connect("/ws") as ws:
            _intro(ws)
            ws.send_text("this is not json {")
            frame = ws.receive_json()
            assert frame["type"] == "error"
            assert frame["message"] == BROKEN_MESSAGE_TEXT

    def test_unknown_message_type_returns_unknown_shape(self, client, limiter):
        limiter()
        with client.websocket_connect("/ws") as ws:
            _intro(ws)
            ws.send_json({"type": "telepathy"})
            frame = ws.receive_json()
            assert frame["type"] == "error"
            assert frame["message"] == UNKNOWN_MESSAGE_TEXT

    def test_input_round_trip_returns_render_frame(self, client, limiter):
        limiter()
        with client.websocket_connect("/ws") as ws:
            _intro(ws)
            ws.send_json({"type": "keypress"})  # dismiss intro -> room
            ws.receive_json()
            ws.send_json({"type": "input", "text": "look"})
            frame = ws.receive_json()
            assert frame["type"] == "render"
            assert any("Health:" in line for line in frame["lines"])


class TestRateLimitingAndValidation:
    def test_per_message_rate_limit_returns_settle_text(self, client, limiter):
        limiter(max_messages_per_min=0)
        with client.websocket_connect("/ws") as ws:
            _intro(ws)
            ws.send_json({"type": "input", "text": "look"})
            frame = ws.receive_json()
            assert frame["type"] == "error"
            assert frame["message"] == RATE_LIMIT_TEXT

    def test_overlong_input_returns_validation_error(self, client, limiter):
        limiter(max_input_length=5)
        with client.websocket_connect("/ws") as ws:
            _intro(ws)
            ws.send_json({"type": "input", "text": "x" * 6})
            frame = ws.receive_json()
            assert frame["type"] == "error"
            assert "crowded" in frame["message"]


class TestIdleTimeout:
    def test_idle_timeout_sends_cold_thread_and_closes(self, client, limiter):
        # Negative timeout makes the idle check fire immediately on loop entry.
        limiter(session_timeout=-1)
        with client.websocket_connect("/ws") as ws:
            _intro(ws)
            frame = ws.receive_json()
            assert frame["type"] == "error"
            assert frame["message"] == SESSION_TIMEOUT_TEXT


class TestSessionCleanup:
    def test_connection_released_on_disconnect(self, client, limiter):
        rl = limiter()
        with client.websocket_connect("/ws") as ws:
            _intro(ws)
            assert rl.active_sessions == 1
        # Context exit disconnects the client; server's finally releases the slot.
        assert rl.active_sessions == 0

    def test_connection_released_when_session_raises(self, client, limiter, monkeypatch):
        rl = limiter()

        class _Boom:
            def get_intro_frame(self):
                from server.protocol import RenderFrame
                return RenderFrame(lines=["intro"], wait_for_key=True)

            def handle_input(self, text):
                raise RuntimeError("session blew up")

        monkeypatch.setattr(app_module, "WebGameSession", _Boom)

        # Sending input makes the stub session raise; the endpoint's
        # except/finally must still release the connection slot. Exiting the
        # context manager joins the server task, so the release has happened.
        with client.websocket_connect("/ws") as ws:
            _intro(ws)
            ws.send_json({"type": "input", "text": "look"})
        assert rl.active_sessions == 0


class TestClientIp:
    """Client IP derivation must not trust the spoofable left-most XFF."""

    @staticmethod
    def _ws(headers, client_host="203.0.113.9"):
        client = SimpleNamespace(host=client_host) if client_host else None
        return SimpleNamespace(headers=headers, client=client)

    def test_prefers_platform_header_over_spoofed_xff(self):
        ws = self._ws({"fly-client-ip": "198.51.100.7", "x-forwarded-for": "1.2.3.4"})
        assert app_module._client_ip(ws) == "198.51.100.7"

    def test_falls_back_to_socket_peer_not_xff_head(self):
        ws = self._ws({"x-forwarded-for": "1.2.3.4, 10.0.0.1"}, client_host="10.0.0.1")
        assert app_module._client_ip(ws) == "10.0.0.1"

    def test_xff_last_hop_used_only_without_peer(self):
        ws = self._ws({"x-forwarded-for": "1.2.3.4, 10.0.0.1"}, client_host=None)
        assert app_module._client_ip(ws) == "10.0.0.1"


class TestOriginAllowlist:
    def test_disallowed_origin_refused(self, client, limiter, monkeypatch):
        limiter()
        monkeypatch.setenv("CABIN_ALLOWED_ORIGINS", "https://www.the-cabin.fi")
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect(
                "/ws", headers={"origin": "https://evil.example"}
            ) as ws:
                _intro(ws)

    def test_allowed_origin_connects(self, client, limiter, monkeypatch):
        limiter()
        monkeypatch.setenv("CABIN_ALLOWED_ORIGINS", "https://www.the-cabin.fi")
        with client.websocket_connect(
            "/ws", headers={"origin": "https://www.the-cabin.fi"}
        ) as ws:
            assert _intro(ws)["type"] == "render"

    def test_missing_origin_allowed(self, client, limiter):
        limiter()
        with client.websocket_connect("/ws") as ws:
            assert _intro(ws)["type"] == "render"


class TestWebSessionSaveDir:
    def test_session_does_not_create_dir_on_init(self):
        session = WebGameSession()
        assert not session.save_manager.save_dir.exists()

    def test_cleanup_removes_created_dir(self, tmp_path):
        session = WebGameSession()
        session.save_manager.save_dir = tmp_path / "web" / "abc"
        session.save_manager._ensure_save_dir()
        assert session.save_manager.save_dir.exists()
        app_module._cleanup_session_saves(session)
        assert not session.save_manager.save_dir.exists()

    def test_cleanup_tolerates_session_without_save_manager(self):
        # Runs in the connection finally block, so it must never raise.
        app_module._cleanup_session_saves(SimpleNamespace())
