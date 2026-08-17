"""Parity and durability proofs for the embedded-Python session adapter."""

from __future__ import annotations

import json

import pytest

from game.persistence import SaveManager
from server.local_engine import InvalidSnapshot, LocalEngine, TurnMismatch
from server.protocol import SessionPhase
from server.session import WebGameSession


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)


def _turn(kind: str, text: str | None = None) -> dict:
    payload = {"type": kind}
    if text is not None:
        payload["text"] = text
    return payload


def _paired_run(tmp_path):
    direct = WebGameSession()
    direct.save_manager = SaveManager(tmp_path / "direct-saves")
    local = LocalEngine(tmp_path / "local")
    assert local.open()["frame"] == direct.get_intro_frame().to_dict()
    return direct, local


def test_adapter_frames_match_web_session_across_runtime_surfaces(tmp_path):
    """The adapter adds durability, not a second implementation of play."""
    direct, local = _paired_run(tmp_path)
    sequence = [
        (_turn("keypress"), ""),
        (_turn("input", "look"), "look"),
        (_turn("input", "save phone"), "save phone"),
        (_turn("input", "north"), "north"),
        (_turn("input", "load phone"), "load phone"),
        (_turn("input", "load act4_night"), "load act4_night"),
        (_turn("input", "map"), "map"),
        (_turn("keypress"), ""),
        (_turn("input", "quit"), "quit"),
    ]
    for turn_id, (payload, text) in enumerate(sequence, start=1):
        expected = direct.handle_input(text).to_dict()
        observed = local.send(turn_id, payload)["frame"]
        assert observed == expected, (turn_id, payload)


@pytest.mark.parametrize(
    ("setup", "phase"),
    [
        ([], SessionPhase.INTRO_KEYPRESS),
        ([(_turn("keypress"), "")], SessionPhase.AWAITING_INPUT),
        (
            [(_turn("keypress"), ""), (_turn("input", "map"), "map")],
            SessionPhase.OVERLAY_KEYPRESS,
        ),
        (
            [(_turn("keypress"), ""), (_turn("input", "quit"), "quit")],
            SessionPhase.ENDED,
        ),
    ],
)
def test_every_session_phase_restores_exactly(tmp_path, setup, phase):
    direct, local = _paired_run(tmp_path)
    for turn_id, (payload, text) in enumerate(setup, start=1):
        assert local.send(turn_id, payload)["frame"] == direct.handle_input(text).to_dict()

    restored = LocalEngine(tmp_path / "local")
    restored.adopt(local.resume_handle)

    assert restored.session.phase == phase
    assert restored._snapshot()["session"] == local._snapshot()["session"]
    assert restored._snapshot()["game_state"] == local._snapshot()["game_state"]


def test_crash_window_replays_completed_turn_without_advancing(tmp_path):
    _, local = _paired_run(tmp_path)
    stale_handle = local.resume_handle
    payload = _turn("keypress")
    first = local.send(1, payload)

    relaunched = LocalEngine(tmp_path / "local")
    relaunched.adopt(stale_handle)
    replayed = relaunched.send(1, payload)

    assert replayed == first
    assert relaunched.next_turn_id == 2


def test_reused_turn_id_with_another_body_fails_closed(tmp_path):
    _, local = _paired_run(tmp_path)
    local.send(1, _turn("keypress"))

    with pytest.raises(TurnMismatch, match="already used"):
        local.send(1, _turn("input", "look"))


def test_out_of_sequence_turn_fails_closed(tmp_path):
    _, local = _paired_run(tmp_path)

    with pytest.raises(TurnMismatch, match="out of sequence"):
        local.send(2, _turn("keypress"))


def test_future_or_corrupt_snapshot_is_not_partially_restored(tmp_path):
    _, local = _paired_run(tmp_path)
    path = local._checkpoint_path(local.run_id)
    snapshot = json.loads(path.read_text(encoding="utf-8"))
    snapshot["version"] = 999
    path.write_text(json.dumps(snapshot), encoding="utf-8")
    restored = LocalEngine(tmp_path / "local")

    with pytest.raises(InvalidSnapshot, match="unsupported version"):
        restored.adopt(local.resume_handle)

    assert restored.session is None
    assert restored.resume_handle is None


def test_failed_adoption_discards_a_previously_loaded_run(tmp_path):
    _, local = _paired_run(tmp_path)
    valid_handle = local.resume_handle
    restored = LocalEngine(tmp_path / "local")
    restored.adopt(valid_handle)
    missing_handle = json.dumps(
        {"version": 1, "run_id": "missing", "next_turn_id": 1}
    )

    with pytest.raises(InvalidSnapshot, match="missing or corrupt"):
        restored.adopt(missing_handle)

    assert restored.session is None
    assert restored.resume_handle is None


def test_snapshot_contains_no_model_secret(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "do-not-write-this")
    local = LocalEngine(tmp_path / "local")
    local.open()

    checkpoint = local._checkpoint_path(local.run_id).read_text(encoding="utf-8")

    assert "do-not-write-this" not in checkpoint
    assert "OPENAI_API_KEY" not in checkpoint


def test_dispatch_maps_mismatch_and_lost_without_exposing_tracebacks(tmp_path):
    local = LocalEngine(tmp_path / "local")
    opened = json.loads(local.dispatch(json.dumps({"operation": "open"})))
    assert opened["ok"] is True

    mismatch = json.loads(
        local.dispatch(
            json.dumps(
                {
                    "operation": "send",
                    "turn_id": 2,
                    "turn": _turn("keypress"),
                }
            )
        )
    )
    lost = json.loads(
        LocalEngine(tmp_path / "other").dispatch(
            json.dumps({"operation": "probe"})
        )
    )

    assert mismatch == {
        "ok": False,
        "kind": "mismatch",
        "message": "turn id is out of sequence",
    }
    assert lost["ok"] is False
    assert lost["kind"] == "lost"
