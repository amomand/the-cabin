"""Tests for the token-keyed HTTP session API (server.app).

These run through Starlette's TestClient with no OpenAI key required —
WebGameSession falls back to rule-based parsing. Each test installs a fresh
RateLimiter and SessionStore so limits and expiry can be driven deterministically.
"""

import time

import pytest
from fastapi.testclient import TestClient

import server.app as app_module
from server.app import (
    app,
    BROKEN_MESSAGE_TEXT,
    CONNECTION_REFUSED_TEXT,
    ORIGIN_REFUSED_TEXT,
    RATE_LIMIT_TEXT,
    TURN_FAILED_TEXT,
    UNKNOWN_IDENTITY_TEXT,
    UNKNOWN_MESSAGE_TEXT,
    UNKNOWN_SESSION_TEXT,
)
from server.rate_limiter import RateLimiter
from server.session_store import SessionStore, durable_save_dir
from game.ai_interpreter import clear_response_cache


@pytest.fixture(autouse=True)
def _clear_ai_cache():
    clear_response_cache()
    yield
    clear_response_cache()


@pytest.fixture(autouse=True)
def _isolated_saves(tmp_path, monkeypatch):
    """Keep every test's save writes inside tmp_path.

    CABIN_SAVE_ROOT covers the durable per-client directories, but a
    throwaway session's directory is a relative path chosen by
    WebGameSession, so the working directory has to move too.
    """
    monkeypatch.setenv("CABIN_SAVE_ROOT", str(tmp_path / "saves"))
    monkeypatch.chdir(tmp_path)


@pytest.fixture
def limiter(monkeypatch):
    """Install a fresh RateLimiter and matching SessionStore."""
    def install(**kwargs):
        rl = RateLimiter(**kwargs)
        monkeypatch.setattr(app_module, "rate_limiter", rl)
        store = SessionStore(
            idle_timeout=rl.session_timeout,
            on_release=app_module._release_session_slot,
        )
        monkeypatch.setattr(app_module, "session_store", store)
        monkeypatch.setattr(app_module, "_last_save_prune", 0.0)
        return rl
    return install


@pytest.fixture
def client():
    return TestClient(app)


def _open(client, **body) -> tuple[str, dict]:
    resp = client.post("/session", json=body)
    assert resp.status_code == 200, resp.text
    payload = resp.json()
    return payload["token"], payload["frame"]


def _turn(client, token, **body):
    return client.post(
        "/session/turn", json=body, headers={"authorization": f"Bearer {token}"}
    )


def _turn_request(client, token, turn_id: int, text: str):
    return _turn(
        client,
        token,
        type="input",
        text=text,
        turn_id=turn_id,
    )


class TestSessionCreation:
    def test_returns_token_and_intro_frame(self, client, limiter):
        limiter()
        token, frame = _open(client)
        assert token
        assert frame["type"] == "render"
        assert "You shouldn't have come back." in frame["lines"]
        assert frame["wait_for_key"] is True

    def test_empty_body_is_accepted(self, client, limiter):
        limiter()
        resp = client.post("/session")
        assert resp.status_code == 200
        assert resp.json()["token"]

    def test_tokens_are_unique_per_session(self, client, limiter):
        limiter()
        first, _ = _open(client)
        second, _ = _open(client)
        assert first != second

    def test_malformed_body_returns_broken_words(self, client, limiter):
        limiter()
        resp = client.post(
            "/session",
            content="not json {",
            headers={"content-type": "application/json"},
        )
        assert resp.status_code == 400
        assert resp.json()["message"] == BROKEN_MESSAGE_TEXT

    def test_non_object_body_returns_broken_words(self, client, limiter):
        limiter()
        resp = client.post("/session", json=["a", "list"])
        assert resp.status_code == 400
        assert resp.json()["message"] == BROKEN_MESSAGE_TEXT

    def test_capacity_refusal_is_narrated(self, client, limiter):
        limiter(max_sessions=0)
        resp = client.post("/session", json={})
        assert resp.status_code == 429
        assert resp.json() == {"type": "error", "message": CONNECTION_REFUSED_TEXT}

    def test_session_counts_against_the_global_cap(self, client, limiter):
        rl = limiter()
        _open(client)
        assert rl.active_sessions == 1


class TestTurns:
    def test_keypress_dismisses_intro_and_renders_room(self, client, limiter):
        limiter()
        token, _ = _open(client)
        resp = _turn(client, token, type="keypress")
        assert resp.status_code == 200
        frame = resp.json()
        assert frame["type"] == "render"
        assert any("Wilderness" in line for line in frame["lines"])
        assert frame["prompt"] == "> "

    def test_input_round_trip_returns_render_frame(self, client, limiter):
        limiter()
        token, _ = _open(client)
        _turn(client, token, type="keypress")
        frame = _turn(client, token, type="input", text="look").json()
        assert frame["type"] == "render"
        assert any("Health:" in line for line in frame["lines"])

    def test_state_survives_between_requests(self, client, limiter):
        """The point of the whole endpoint: no socket, but the run persists."""
        limiter()
        token, _ = _open(client)
        _turn(client, token, type="keypress")
        first = _turn(client, token, type="input", text="look").json()
        second = _turn(client, token, type="input", text="look").json()
        assert first["lines"] == second["lines"]

    def test_unknown_message_type_is_narrated(self, client, limiter):
        limiter()
        token, _ = _open(client)
        resp = _turn(client, token, type="telepathy")
        assert resp.status_code == 400
        assert resp.json()["message"] == UNKNOWN_MESSAGE_TEXT

    def test_non_string_text_is_narrated(self, client, limiter):
        limiter()
        token, _ = _open(client)
        resp = _turn(client, token, type="input", text=17)
        assert resp.status_code == 400
        assert resp.json()["message"] == UNKNOWN_MESSAGE_TEXT

    def test_non_object_body_is_narrated(self, client, limiter):
        limiter()
        token, _ = _open(client)
        resp = client.post(
            "/session/turn",
            json=["not", "a", "message"],
            headers={"authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 400
        assert resp.json()["message"] == UNKNOWN_MESSAGE_TEXT

    def test_malformed_body_is_narrated(self, client, limiter):
        limiter()
        token, _ = _open(client)
        resp = client.post(
            "/session/turn",
            content="{{{",
            headers={
                "content-type": "application/json",
                "authorization": f"Bearer {token}",
            },
        )
        assert resp.status_code == 400
        assert resp.json()["message"] == BROKEN_MESSAGE_TEXT

    def test_overlong_input_is_narrated(self, client, limiter):
        limiter(max_input_length=5)
        token, _ = _open(client)
        resp = _turn(client, token, type="input", text="x" * 6)
        assert resp.status_code == 400
        assert "crowded" in resp.json()["message"]

    def test_rate_limited_turn_is_narrated(self, client, limiter):
        limiter(max_messages_per_min=0)
        token, _ = _open(client)
        resp = _turn(client, token, type="keypress")
        assert resp.status_code == 429
        assert resp.json()["message"] == RATE_LIMIT_TEXT


class TestIdempotentTurns:
    def test_repeat_replays_the_exact_frame_and_advances_once(self, client, limiter):
        from server.protocol import RenderFrame

        limiter()
        token, _ = _open(client)
        stored = app_module.session_store.get(token)
        calls = []

        def _turn(text):
            calls.append(text)
            return RenderFrame(lines=[f"turn {len(calls)}: {text}"], prompt="> ")

        stored.session.handle_input = _turn

        first = _turn_request(client, token, 1, "look")
        repeated = _turn_request(client, token, 1, "look")

        assert first.status_code == repeated.status_code == 200
        assert repeated.json() == first.json()
        assert calls == ["look"]

    def test_next_id_advances_after_a_replay(self, client, limiter):
        from server.protocol import RenderFrame

        limiter()
        token, _ = _open(client)
        stored = app_module.session_store.get(token)
        calls = []
        stored.session.handle_input = lambda text: (
            calls.append(text) or RenderFrame(lines=[text], prompt="> ")
        )

        _turn_request(client, token, 1, "look")
        _turn_request(client, token, 1, "look")
        second = _turn_request(client, token, 2, "north")

        assert second.status_code == 200
        assert second.json()["lines"] == ["north"]
        assert calls == ["look", "north"]

    @pytest.mark.parametrize("turn_id", [0, -1, True, "1", 1.5])
    def test_invalid_id_is_refused_without_advancing(
        self, client, limiter, turn_id
    ):
        limiter()
        token, _ = _open(client)
        stored = app_module.session_store.get(token)
        calls = []
        stored.session.handle_input = lambda text: calls.append(text)

        resp = _turn(
            client, token, type="input", text="look", turn_id=turn_id
        )

        assert resp.status_code == 400
        assert resp.json()["message"] == BROKEN_MESSAGE_TEXT
        assert calls == []

    def test_stale_or_skipped_id_is_refused_without_advancing(self, client, limiter):
        from server.protocol import RenderFrame

        limiter()
        token, _ = _open(client)
        stored = app_module.session_store.get(token)
        calls = []
        stored.session.handle_input = lambda text: (
            calls.append(text) or RenderFrame(lines=[text], prompt="> ")
        )

        assert _turn_request(client, token, 1, "look").status_code == 200
        assert _turn_request(client, token, 2, "north").status_code == 200
        stale = _turn_request(client, token, 1, "look")
        skipped = _turn_request(client, token, 4, "south")

        assert stale.status_code == skipped.status_code == 400
        assert calls == ["look", "north"]

    def test_reusing_current_id_for_different_input_is_refused(self, client, limiter):
        from server.protocol import RenderFrame

        limiter()
        token, _ = _open(client)
        stored = app_module.session_store.get(token)
        calls = []
        stored.session.handle_input = lambda text: (
            calls.append(text) or RenderFrame(lines=[text], prompt="> ")
        )

        assert _turn_request(client, token, 1, "look").status_code == 200
        changed = _turn_request(client, token, 1, "north")

        assert changed.status_code == 400
        assert calls == ["look"]

    def test_absent_id_keeps_legacy_turn_behaviour(self, client, limiter):
        from server.protocol import RenderFrame

        limiter()
        token, _ = _open(client)
        stored = app_module.session_store.get(token)
        calls = []
        stored.session.handle_input = lambda text: (
            calls.append(text) or RenderFrame(lines=[text], prompt="> ")
        )

        assert _turn(client, token, type="input", text="look").status_code == 200
        assert _turn(client, token, type="input", text="look").status_code == 200
        assert calls == ["look", "look"]

    def test_game_over_replay_survives_session_release(self, client, limiter):
        from server.protocol import RenderFrame

        rl = limiter()
        token, _ = _open(client)
        stored = app_module.session_store.get(token)
        calls = []
        stored.session.handle_input = lambda text: (
            calls.append(text) or RenderFrame(lines=["It is over."], game_over=True)
        )

        first = _turn_request(client, token, 1, "wait")
        repeated = _turn_request(client, token, 1, "wait")

        assert first.status_code == repeated.status_code == 200
        assert repeated.json() == first.json()
        assert calls == ["wait"]
        assert app_module.session_store.get(token) is None
        assert rl.active_sessions == 0


class TestUnknownAndExpiredTokens:
    def test_unknown_token_is_narrated_not_bare(self, client, limiter):
        limiter()
        resp = _turn(client, "no-such-token", type="keypress")
        assert resp.status_code == 404
        assert resp.json() == {"type": "error", "message": UNKNOWN_SESSION_TEXT}

    def test_expired_token_is_narrated(self, client, limiter):
        limiter(session_timeout=-1)  # everything is already idle past the grace
        token, _ = _open(client)
        resp = _turn(client, token, type="keypress")
        assert resp.status_code == 404
        assert resp.json()["message"] == UNKNOWN_SESSION_TEXT

    def test_expiry_frees_the_session_slot(self, client, limiter):
        rl = limiter(session_timeout=-1)
        _open(client)
        assert rl.active_sessions == 1
        client.get("/health")
        assert rl.active_sessions == 0

    def test_expiry_does_not_end_a_live_session(self, client, limiter):
        rl = limiter(session_timeout=3600)
        token, _ = _open(client)
        client.get("/health")
        assert rl.active_sessions == 1
        assert _turn(client, token, type="keypress").status_code == 200


class TestSaveDurability:
    def test_throwaway_dir_is_removed_on_release(self, client, limiter):
        limiter()
        token, _ = _open(client)
        stored = app_module.session_store.get(token)
        save_dir = stored.session.save_manager.save_dir
        stored.session.save_manager._ensure_save_dir()
        assert save_dir.exists()

        app_module.session_store.release(token)
        assert not save_dir.exists()

    def test_throwaway_dir_is_removed_at_expiry(self, client, limiter):
        limiter()
        token, _ = _open(client)
        stored = app_module.session_store.get(token)
        save_dir = stored.session.save_manager.save_dir
        stored.session.save_manager._ensure_save_dir()
        assert save_dir.exists()

        app_module.session_store.idle_timeout = -1
        app_module.rate_limiter.session_timeout = -1
        client.get("/health")  # sweeps
        assert not save_dir.exists()

    def test_client_identity_gets_a_durable_dir(self, client, limiter):
        limiter()
        client_id = "a" * 32
        token, _ = _open(client, client_id=client_id)
        stored = app_module.session_store.get(token)
        assert stored.session.save_manager.save_dir == durable_save_dir(client_id)

    def test_durable_dir_survives_release(self, client, limiter):
        limiter()
        client_id = "b" * 32
        token, _ = _open(client, client_id=client_id)
        stored = app_module.session_store.get(token)
        stored.session.save_manager._ensure_save_dir()
        save_dir = stored.session.save_manager.save_dir

        app_module.session_store.release(token)
        assert save_dir.exists()

    def test_a_second_run_retires_the_first_for_one_identity(self, client, limiter):
        """Two live sessions must never write the same save files."""
        rl = limiter()
        client_id = "c" * 32
        first, _ = _open(client, client_id=client_id)
        second, _ = _open(client, client_id=client_id)

        assert app_module.session_store.get(first) is None
        stored = app_module.session_store.get(second)
        assert stored.session.save_manager.save_dir == durable_save_dir(client_id)
        assert rl.active_sessions == 1

    def test_retired_session_token_is_narrated(self, client, limiter):
        limiter()
        client_id = "e" * 32
        first, _ = _open(client, client_id=client_id)
        _open(client, client_id=client_id)
        resp = _turn(client, first, type="keypress")
        assert resp.status_code == 404
        assert resp.json()["message"] == UNKNOWN_SESSION_TEXT

    def test_anonymous_sessions_do_not_retire_each_other(self, client, limiter):
        rl = limiter()
        first, _ = _open(client)
        second, _ = _open(client)
        assert app_module.session_store.get(first) is not None
        assert app_module.session_store.get(second) is not None
        assert rl.active_sessions == 2

    @pytest.mark.parametrize(
        "bad",
        ["short", "../../etc/passwd", "has space" * 3, "x" * 129, ""],
    )
    def test_malformed_identity_is_refused(self, client, limiter, bad):
        limiter()
        resp = client.post("/session", json={"client_id": bad})
        assert resp.status_code == 400
        assert resp.json()["message"] == UNKNOWN_IDENTITY_TEXT

    def test_non_string_identity_is_refused(self, client, limiter):
        limiter()
        resp = client.post("/session", json={"client_id": 12345})
        assert resp.status_code == 400
        assert resp.json()["message"] == UNKNOWN_IDENTITY_TEXT


class TestGameOver:
    def test_game_over_releases_the_session(self, client, limiter, monkeypatch):
        rl = limiter()
        token, _ = _open(client)
        stored = app_module.session_store.get(token)

        from server.protocol import RenderFrame

        monkeypatch.setattr(
            stored.session,
            "handle_input",
            lambda text: RenderFrame(lines=["the cold has had its turn"], game_over=True),
        )

        frame = _turn(client, token, type="input", text="wait").json()
        assert frame["game_over"] is True
        assert app_module.session_store.get(token) is None
        assert rl.active_sessions == 0


class TestParityWithWebSocket:
    def test_same_input_sequence_yields_the_same_frames(self, client, limiter):
        """Both surfaces run the same WebGameSession; frames must not drift."""
        sequence = [
            {"type": "keypress"},
            {"type": "input", "text": "look"},
            {"type": "input", "text": "inventory"},
            {"type": "input", "text": "north"},
        ]

        limiter()
        with client.websocket_connect("/ws") as ws:
            ws_frames = [ws.receive_json()]
            for msg in sequence:
                ws.send_json(msg)
                ws_frames.append(ws.receive_json())

        clear_response_cache()
        limiter()
        token, intro = _open(client)
        http_frames = [intro]
        for msg in sequence:
            resp = _turn(client, token, **msg)
            assert resp.status_code == 200, resp.text
            http_frames.append(resp.json())

        assert http_frames == ws_frames

    @pytest.mark.parametrize(
        "message",
        [
            {"type": "telepathy"},
            {"type": "input", "text": 17},
            {"no": "type at all"},
            ["not", "a", "message"],
            "a bare string",
            17,
        ],
        ids=[
            "unknown-type",
            "non-string-text",
            "missing-type",
            "json-array",
            "json-string",
            "json-number",
        ],
    )
    def test_odd_payloads_are_narrated_the_same_on_both_surfaces(
        self, client, limiter, message
    ):
        """Neither surface may crash, and neither may answer differently."""
        limiter()
        with client.websocket_connect("/ws") as ws:
            ws.receive_json()
            ws.send_json(message)
            ws_reply = ws.receive_json()
            # The socket must survive: a valid turn still works afterwards.
            ws.send_json({"type": "keypress"})
            assert ws.receive_json()["type"] == "render"

        limiter()
        token, _ = _open(client)
        resp = client.post(
            "/session/turn",
            json=message,
            headers={"authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 400
        assert resp.json() == ws_reply
        # The session must survive too.
        assert _turn(client, token, type="keypress").status_code == 200

    def test_unparseable_text_is_narrated_the_same_on_both_surfaces(
        self, client, limiter
    ):
        limiter()
        with client.websocket_connect("/ws") as ws:
            ws.receive_json()
            ws.send_text("this is not json {")
            ws_reply = ws.receive_json()

        limiter()
        token, _ = _open(client)
        resp = client.post(
            "/session/turn",
            content="this is not json {",
            headers={
                "content-type": "application/json",
                "authorization": f"Bearer {token}",
            },
        )
        assert resp.status_code == 400
        assert resp.json() == ws_reply

    def test_overlong_input_is_narrated_the_same_on_both_surfaces(self, client, limiter):
        limiter(max_input_length=5)
        with client.websocket_connect("/ws") as ws:
            ws.receive_json()
            ws.send_json({"type": "input", "text": "x" * 6})
            ws_reply = ws.receive_json()

        limiter(max_input_length=5)
        token, _ = _open(client)
        resp = _turn(client, token, type="input", text="x" * 6)
        assert resp.json() == ws_reply


class TestAuthorizationHeader:
    def test_missing_header_is_narrated(self, client, limiter):
        limiter()
        _open(client)
        resp = client.post("/session/turn", json={"type": "keypress"})
        assert resp.status_code == 404
        assert resp.json()["message"] == UNKNOWN_SESSION_TEXT

    @pytest.mark.parametrize(
        "header", ["", "Bearer", "Bearer   ", "Basic abc", "token abc"]
    )
    def test_malformed_header_is_narrated(self, client, limiter, header):
        limiter()
        resp = client.post(
            "/session/turn",
            json={"type": "keypress"},
            headers={"authorization": header},
        )
        assert resp.status_code == 404
        assert resp.json()["message"] == UNKNOWN_SESSION_TEXT

    def test_scheme_is_case_insensitive(self, client, limiter):
        limiter()
        token, _ = _open(client)
        resp = client.post(
            "/session/turn",
            json={"type": "keypress"},
            headers={"authorization": f"bEaReR {token}"},
        )
        assert resp.status_code == 200

    def test_token_never_appears_in_the_request_path(self, client, limiter):
        """Tokens are bearer secrets; they must stay out of access logs."""
        limiter()
        token, _ = _open(client)
        resp = _turn(client, token, type="keypress")
        assert token not in str(resp.request.url)


class TestOriginAllowlistOnHttp:
    def test_unlisted_origin_is_refused(self, client, limiter, monkeypatch):
        limiter()
        monkeypatch.setenv("CABIN_ALLOWED_ORIGINS", "https://www.the-cabin.fi")
        resp = client.post(
            "/session", json={}, headers={"origin": "https://evil.example"}
        )
        assert resp.status_code == 403
        assert resp.json()["message"] == ORIGIN_REFUSED_TEXT

    def test_allowed_origin_is_accepted(self, client, limiter, monkeypatch):
        limiter()
        monkeypatch.setenv("CABIN_ALLOWED_ORIGINS", "https://www.the-cabin.fi")
        resp = client.post(
            "/session", json={}, headers={"origin": "https://www.the-cabin.fi"}
        )
        assert resp.status_code == 200

    def test_absent_origin_is_accepted(self, client, limiter, monkeypatch):
        """Native clients send no Origin and must not be locked out."""
        limiter()
        monkeypatch.setenv("CABIN_ALLOWED_ORIGINS", "https://www.the-cabin.fi")
        assert client.post("/session", json={}).status_code == 200

    def test_turn_from_an_unlisted_origin_is_refused(self, client, limiter, monkeypatch):
        limiter()
        token, _ = _open(client)
        monkeypatch.setenv("CABIN_ALLOWED_ORIGINS", "https://www.the-cabin.fi")
        resp = client.post(
            "/session/turn",
            json={"type": "keypress"},
            headers={
                "authorization": f"Bearer {token}",
                "origin": "https://evil.example",
            },
        )
        assert resp.status_code == 403

    def test_refused_origin_does_not_open_a_session(self, client, limiter, monkeypatch):
        rl = limiter()
        monkeypatch.setenv("CABIN_ALLOWED_ORIGINS", "https://www.the-cabin.fi")
        client.post("/session", json={}, headers={"origin": "https://evil.example"})
        assert rl.active_sessions == 0
        assert len(app_module.session_store) == 0


class TestBodyLimits:
    def test_oversized_create_body_is_refused(self, client, limiter):
        limiter()
        resp = client.post("/session", json={"client_id": "a" * 20000})
        assert resp.status_code == 413
        assert resp.json()["message"] == BROKEN_MESSAGE_TEXT

    def test_oversized_turn_body_is_refused(self, client, limiter):
        limiter()
        token, _ = _open(client)
        resp = _turn(client, token, type="input", text="x" * 20000)
        assert resp.status_code == 413

    def test_oversized_body_does_not_open_a_session(self, client, limiter):
        rl = limiter()
        client.post("/session", json={"client_id": "a" * 20000})
        assert rl.active_sessions == 0

    def test_lying_content_length_is_still_caught(self, client, limiter):
        """A chunked request declares no length, so the stream must be measured."""
        limiter()

        def _chunks():
            yield b'{"client_id": "'
            yield b"a" * 20000
            yield b'"}'

        resp = client.post(
            "/session",
            content=_chunks(),
            headers={"content-type": "application/json"},
        )
        assert resp.status_code == 413


class TestTurnFailure:
    def test_failed_turn_is_narrated_and_frees_the_slot(self, client, limiter):
        rl = limiter()
        token, _ = _open(client)
        stored = app_module.session_store.get(token)

        def _boom(text):
            raise RuntimeError("the session blew up")

        stored.session.handle_input = _boom

        resp = _turn(client, token, type="keypress")
        assert resp.status_code == 500
        assert resp.json() == {"type": "error", "message": TURN_FAILED_TEXT}
        assert app_module.session_store.get(token) is None
        assert rl.active_sessions == 0

    def test_failed_session_creation_frees_the_slot(self, client, limiter, monkeypatch):
        rl = limiter()

        def _boom(**kwargs):
            raise RuntimeError("no session for you")

        monkeypatch.setattr(app_module.session_store, "create", _boom)
        resp = client.post("/session", json={})
        assert resp.status_code == 500
        assert resp.json()["message"] == TURN_FAILED_TEXT
        assert rl.active_sessions == 0


class TestConcurrentTurns:
    def test_turns_for_one_session_do_not_overlap(self, client, limiter):
        """A double-tapped send must not run two turns against one game state."""
        import asyncio

        import httpx

        from server.protocol import RenderFrame

        limiter()
        token, _ = _open(client)
        stored = app_module.session_store.get(token)

        import threading

        in_flight = 0
        max_in_flight = 0
        entered = threading.Event()
        release = threading.Event()

        def _slow_turn(text):
            nonlocal in_flight, max_in_flight
            in_flight += 1
            max_in_flight = max(max_in_flight, in_flight)
            entered.set()
            # Held open by the test, not by a timing guess: the second request
            # is already issued, so if the lock were missing it would enter
            # here and push max_in_flight to 2.
            release.wait(timeout=5)
            in_flight -= 1
            return RenderFrame(lines=["a turn"])

        stored.session.handle_input = _slow_turn

        async def _fire_both():
            transport = httpx.ASGITransport(app=app)
            headers = {"authorization": f"Bearer {token}"}
            loop = asyncio.get_running_loop()
            async with httpx.AsyncClient(
                transport=transport, base_url="http://testserver"
            ) as ac:
                both = asyncio.gather(
                    ac.post(
                        "/session/turn",
                        json={"type": "input", "text": "a"},
                        headers=headers,
                    ),
                    ac.post(
                        "/session/turn",
                        json={"type": "input", "text": "b"},
                        headers=headers,
                    ),
                )
                # Wait until a turn is genuinely executing, then let the event
                # loop run so the second request reaches the lock.
                await loop.run_in_executor(None, entered.wait, 5)
                assert entered.is_set(), "no turn reached the executor"
                for _ in range(20):
                    await asyncio.sleep(0)
                overlapped = max_in_flight
                release.set()
                return await both, overlapped

        responses, overlapped = asyncio.run(_fire_both())

        assert [r.status_code for r in responses] == [200, 200]
        assert overlapped == 1
        assert max_in_flight == 1

    def test_repeat_waits_for_the_original_then_replays_it(self, client, limiter):
        """A retry arriving mid-turn must not advance state a second time."""
        import asyncio
        import threading

        import httpx

        from server.protocol import RenderFrame

        limiter(max_messages_per_min=10)
        token, _ = _open(client)
        stored = app_module.session_store.get(token)
        entered = threading.Event()
        release = threading.Event()
        calls = 0

        def _slow_turn(text):
            nonlocal calls
            calls += 1
            entered.set()
            release.wait(timeout=5)
            return RenderFrame(lines=["one turn"], prompt="> ")

        stored.session.handle_input = _slow_turn

        async def _fire_both():
            transport = httpx.ASGITransport(app=app)
            headers = {"authorization": f"Bearer {token}"}
            body = {"type": "input", "text": "look", "turn_id": 1}
            async with httpx.AsyncClient(
                transport=transport, base_url="http://testserver"
            ) as ac:
                first = asyncio.create_task(
                    ac.post("/session/turn", json=body, headers=headers)
                )
                await asyncio.get_running_loop().run_in_executor(
                    None, entered.wait, 5
                )
                assert entered.is_set(), "the original never reached the executor"
                repeated = asyncio.create_task(
                    ac.post("/session/turn", json=body, headers=headers)
                )
                for _ in range(20):
                    await asyncio.sleep(0)
                release.set()
                return await first, await repeated

        first, repeated = asyncio.run(_fire_both())

        assert first.status_code == repeated.status_code == 200
        assert repeated.json() == first.json()
        assert calls == 1


class TestSavePruning:
    def test_prune_runs_at_most_once_per_interval(self, client, limiter, monkeypatch):
        limiter()
        calls = []
        monkeypatch.setattr(
            app_module,
            "prune_expired_saves",
            lambda live: calls.append(live) or [],
        )
        _open(client)
        _open(client)
        assert len(calls) == 1

    def test_prune_is_told_which_dirs_are_live(self, client, limiter, monkeypatch):
        limiter()
        calls = []
        monkeypatch.setattr(
            app_module,
            "prune_expired_saves",
            lambda live: calls.append(set(live)) or [],
        )
        token, _ = _open(client, client_id="p" * 32)
        stored = app_module.session_store.get(token)

        monkeypatch.setattr(app_module, "_last_save_prune", 0.0)
        _open(client)
        assert stored.session.save_manager.save_dir in calls[-1]


class TestCreationSlotAccounting:
    """A create that never yields a session must hand its slot back."""

    @pytest.mark.parametrize(
        "post",
        [
            lambda c: c.post("/session", content=b"{" * 4, headers={
                "content-type": "application/json"}),
            lambda c: c.post("/session", json=["not", "an", "object"]),
            lambda c: c.post("/session", json={"client_id": "short"}),
            lambda c: c.post("/session", json={"client_id": 17}),
        ],
        ids=["unparseable", "non-object", "bad-identity", "non-string-identity"],
    )
    def test_refused_create_does_not_consume_a_session_slot(
        self, client, limiter, post
    ):
        rl = limiter(max_sessions=1)
        resp = post(client)
        assert resp.status_code in (400, 413)
        assert rl.active_sessions == 0
        # The slot is genuinely free: a good create still succeeds.
        assert client.post("/session", json={}).status_code == 200

    def test_refused_create_still_costs_a_connection_attempt(self, client, limiter):
        """Otherwise malformed bodies are a free way to probe the endpoint."""
        rl = limiter(max_connections_per_min=2)
        assert client.post("/session", json=["nope"]).status_code == 400
        assert client.post("/session", json=["nope"]).status_code == 400
        assert client.post("/session", json={}).status_code == 429
        assert rl.active_sessions == 0

    def test_failed_session_construction_releases_the_slot(
        self, client, limiter, monkeypatch
    ):
        rl = limiter()

        def _boom(**kwargs):
            raise RuntimeError("no session for you")

        monkeypatch.setattr(app_module.session_store, "create", _boom)
        resp = client.post("/session", json={})
        assert resp.status_code == 500
        assert resp.json()["message"] == TURN_FAILED_TEXT
        assert rl.active_sessions == 0


class TestIdentityBusy:
    def test_second_create_is_refused_while_the_first_is_mid_turn(
        self, client, limiter
    ):
        """Retiring a mid-turn session would leave two writers on one save dir."""
        import asyncio

        import httpx

        from server.protocol import RenderFrame

        limiter()
        client_id = "b" * 32
        token, _ = _open(client, client_id=client_id)
        stored = app_module.session_store.get(token)
        save_dir = stored.session.save_manager.save_dir

        import threading

        # Events rather than sleeps: the create must happen while the turn is
        # genuinely in flight, and a timing guess would make that either flaky
        # or silently trivial on a slow machine.
        turn_started = threading.Event()
        may_finish = threading.Event()

        def _slow_turn(text):
            turn_started.set()
            may_finish.wait(timeout=5)
            return RenderFrame(lines=["a slow turn"])

        stored.session.handle_input = _slow_turn

        async def _turn_then_create():
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(
                transport=transport, base_url="http://testserver"
            ) as ac:
                turn = asyncio.create_task(
                    ac.post(
                        "/session/turn",
                        json={"type": "input", "text": "slow"},
                        headers={"authorization": f"Bearer {token}"},
                    )
                )
                await asyncio.get_running_loop().run_in_executor(
                    None, turn_started.wait, 5
                )
                assert turn_started.is_set(), "turn never reached the executor"
                create = await ac.post("/session", json={"client_id": client_id})
                may_finish.set()
                return await turn, create

        turn_resp, create_resp = asyncio.run(_turn_then_create())

        assert turn_resp.status_code == 200
        assert create_resp.status_code == 409
        assert create_resp.json()["message"] == app_module.IDENTITY_BUSY_TEXT
        # The original session survived its turn and still owns the directory.
        assert app_module.session_store.get(token) is not None
        assert stored.session.save_manager.save_dir == save_dir

    def test_refusal_does_not_consume_a_session_slot(self, client, limiter):
        rl = limiter()
        client_id = "c" * 32
        token, _ = _open(client, client_id=client_id)
        stored = app_module.session_store.get(token)
        stored.in_flight = 1
        before = rl.active_sessions

        resp = client.post("/session", json={"client_id": client_id})
        assert resp.status_code == 409
        assert rl.active_sessions == before

    def test_idle_session_is_still_replaced_normally(self, client, limiter):
        """Exclusivity must not become a lockout once the turn has landed."""
        limiter()
        client_id = "d" * 32
        first, _ = _open(client, client_id=client_id)
        second, _ = _open(client, client_id=client_id)
        assert first != second
        assert app_module.session_store.get(first) is None
        assert app_module.session_store.get(second) is not None


class TestOverlongIntegerBody:
    """CPython raises a bare ValueError past its integer digit limit."""

    HUGE = b"1" * 5000

    def test_http_narrates_instead_of_500(self, client, limiter):
        limiter()
        token, _ = _open(client)
        resp = client.post(
            "/session/turn",
            content=self.HUGE,
            headers={
                "content-type": "application/json",
                "authorization": f"Bearer {token}",
            },
        )
        assert resp.status_code == 400
        assert resp.json()["message"] == BROKEN_MESSAGE_TEXT

    def test_websocket_survives_it(self, client, limiter):
        limiter()
        with client.websocket_connect("/ws") as ws:
            ws.receive_json()
            ws.send_text(self.HUGE.decode())
            assert ws.receive_json()["message"] == BROKEN_MESSAGE_TEXT
            # The socket is still usable.
            ws.send_json({"type": "keypress"})
            assert ws.receive_json()["type"] == "render"

    def test_create_narrates_it_too(self, client, limiter):
        limiter()
        resp = client.post(
            "/session",
            content=self.HUGE,
            headers={"content-type": "application/json"},
        )
        assert resp.status_code == 400
        assert resp.json()["message"] == BROKEN_MESSAGE_TEXT


class TestConcurrentCreation:
    def test_concurrent_creates_cannot_overshoot_the_session_cap(
        self, client, limiter
    ):
        """The cap is meaningless if the check and the reservation are separated
        by an await: every request passes a stale check while its body streams.
        """
        import asyncio

        import httpx

        rl = limiter(max_sessions=1, max_connections_per_min=10)

        async def _slow_body():
            # A body that arrives in pieces, so the read genuinely yields.
            yield b'{"client'
            await asyncio.sleep(0.05)
            yield b'_id": null}'

        async def _fire_both():
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(
                transport=transport, base_url="http://testserver"
            ) as ac:
                return await asyncio.gather(
                    ac.post("/session", content=_slow_body(),
                            headers={"content-type": "application/json"}),
                    ac.post("/session", content=_slow_body(),
                            headers={"content-type": "application/json"}),
                )

        responses = asyncio.run(_fire_both())
        codes = sorted(r.status_code for r in responses)
        assert codes == [200, 429], codes
        assert rl.active_sessions == 1


def _age(directory, *, days: int) -> None:
    """Backdate a save directory and everything in it."""
    import os

    when = time.time() - (days * 86400)
    for child in directory.iterdir():
        os.utime(child, (when, when))
    os.utime(directory, (when, when))


class TestPruningDoesNotEatTheSessionItIsOpening:
    def test_returning_client_keeps_saves_opened_on_the_boundary(
        self, client, limiter, monkeypatch
    ):
        """Pruning before the session exists would delete the very directory
        the player is about to load from."""
        monkeypatch.setenv("CABIN_SAVE_RETENTION_DAYS", "30")
        limiter()
        client_id = "e" * 32
        save_dir = durable_save_dir(client_id)
        save_dir.mkdir(parents=True, exist_ok=True)
        stale = save_dir / "trip.json"
        stale.write_text("{}")
        # Last written well past the retention window. The directory's own
        # mtime counts too, so age both.
        _age(save_dir, days=31)

        token, _ = _open(client, client_id=client_id)

        assert save_dir.exists()
        assert stale.exists()
        assert app_module.session_store.get(token) is not None

    def test_a_truly_abandoned_dir_is_still_pruned(self, client, limiter, monkeypatch):
        """The protection must not become a blanket amnesty."""
        monkeypatch.setenv("CABIN_SAVE_RETENTION_DAYS", "30")
        limiter()
        abandoned = durable_save_dir("f" * 32)
        abandoned.mkdir(parents=True, exist_ok=True)
        stale = abandoned / "trip.json"
        stale.write_text("{}")
        _age(abandoned, days=31)

        # Someone else opens a session; the abandoned dir is not theirs.
        _open(client, client_id="g" * 32)

        assert not abandoned.exists()
