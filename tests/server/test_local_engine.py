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


def test_resume_handle_more_than_one_turn_behind_dispatches_as_lost(tmp_path):
    _, local = _paired_run(tmp_path)
    stale_handle = local.resume_handle
    local.send(1, _turn("keypress"))
    local.send(2, _turn("input", "look"))
    relaunched = LocalEngine(tmp_path / "local")

    response = json.loads(
        relaunched.dispatch(
            json.dumps({"operation": "adopt", "resume_handle": stale_handle})
        )
    )

    assert response["ok"] is False
    assert response["kind"] == "lost"
    assert relaunched.session is None
    assert relaunched.resume_handle is None


def test_replay_retries_a_checkpoint_that_failed_after_turn_completion(
    tmp_path, monkeypatch
):
    _, local = _paired_run(tmp_path)
    stale_handle = local.resume_handle
    original_checkpoint = local._checkpoint
    attempts = 0

    def fail_once():
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise OSError("storage temporarily unavailable")
        original_checkpoint()

    monkeypatch.setattr(local, "_checkpoint", fail_once)
    request = json.dumps(
        {"operation": "send", "turn_id": 1, "turn": _turn("keypress")}
    )

    failed = json.loads(local.dispatch(request))
    replayed = json.loads(local.dispatch(request))

    assert failed == {
        "ok": False,
        "kind": "internal",
        "message": "local engine failed",
    }
    assert replayed["ok"] is True
    assert attempts == 2
    restored = LocalEngine(tmp_path / "local")
    restored.adopt(stale_handle)
    assert restored.next_turn_id == 2
    assert restored.last_completed["frame"] == replayed["frame"]


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


def test_sparse_nested_game_state_is_rejected_instead_of_default_filled(tmp_path):
    _, local = _paired_run(tmp_path)
    local.send(1, _turn("keypress"))
    local.send(2, _turn("input", "load act4_night"))
    path = local._checkpoint_path(local.run_id)
    snapshot = json.loads(path.read_text(encoding="utf-8"))
    snapshot["game_state"] = {}
    path.write_text(json.dumps(snapshot), encoding="utf-8")
    restored = LocalEngine(tmp_path / "local")

    with pytest.raises(InvalidSnapshot, match="game state is malformed"):
        restored.adopt(local.resume_handle)

    assert restored.session is None


def test_mistyped_nested_game_state_dispatches_as_lost(tmp_path):
    _, local = _paired_run(tmp_path)
    path = local._checkpoint_path(local.run_id)
    snapshot = json.loads(path.read_text(encoding="utf-8"))
    snapshot["game_state"]["map"] = []
    path.write_text(json.dumps(snapshot), encoding="utf-8")
    response = json.loads(
        LocalEngine(tmp_path / "local").dispatch(
            json.dumps(
                {"operation": "adopt", "resume_handle": local.resume_handle}
            )
        )
    )

    assert response["ok"] is False
    assert response["kind"] == "lost"


def test_json_type_changes_in_nested_game_state_are_rejected(tmp_path):
    _, local = _paired_run(tmp_path)
    path = local._checkpoint_path(local.run_id)
    snapshot = json.loads(path.read_text(encoding="utf-8"))
    snapshot["game_state"]["player"]["health"] = True
    path.write_text(json.dumps(snapshot), encoding="utf-8")

    with pytest.raises(InvalidSnapshot, match="game state is malformed"):
        LocalEngine(tmp_path / "local").adopt(local.resume_handle)


@pytest.mark.parametrize(
    ("field", "value"),
    [("health", 9999), ("fear", -7)],
)
def test_impossible_player_stats_in_checkpoint_are_rejected(tmp_path, field, value):
    _, local = _paired_run(tmp_path)
    local.send(1, _turn("keypress"))
    local.send(2, _turn("input", "load act4_night"))
    path = local._checkpoint_path(local.run_id)
    snapshot = json.loads(path.read_text(encoding="utf-8"))
    snapshot["game_state"]["player"][field] = value
    path.write_text(json.dumps(snapshot), encoding="utf-8")

    with pytest.raises(InvalidSnapshot, match="game state is malformed"):
        LocalEngine(tmp_path / "local").adopt(local.resume_handle)


def test_duplicate_anomaly_ids_in_checkpoint_are_rejected(tmp_path):
    _, local = _paired_run(tmp_path)
    local.send(1, _turn("keypress"))
    local.send(2, _turn("input", "load act4_night"))
    path = local._checkpoint_path(local.run_id)
    snapshot = json.loads(path.read_text(encoding="utf-8"))
    entries = snapshot["game_state"]["world_state"]["wrongness"]["entries"]
    assert entries
    entries.append(dict(entries[0]))
    path.write_text(json.dumps(snapshot), encoding="utf-8")

    with pytest.raises(InvalidSnapshot, match="game state is malformed"):
        LocalEngine(tmp_path / "local").adopt(local.resume_handle)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("anomaly_id", "fabricated_tell"),
        ("description", "A different memory of what happened."),
        ("seen_at", 1),
    ],
)
def test_noncanonical_wrongness_entries_dispatch_as_lost(tmp_path, field, value):
    _, local = _paired_run(tmp_path)
    local.send(1, _turn("keypress"))
    local.send(2, _turn("input", "load act4_night"))
    path = local._checkpoint_path(local.run_id)
    snapshot = json.loads(path.read_text(encoding="utf-8"))
    entries = snapshot["game_state"]["world_state"]["wrongness"]["entries"]
    assert entries
    entries[0][field] = value
    path.write_text(json.dumps(snapshot), encoding="utf-8")
    restored = LocalEngine(tmp_path / "local")

    response = json.loads(
        restored.dispatch(
            json.dumps(
                {"operation": "adopt", "resume_handle": local.resume_handle}
            )
        )
    )

    assert response["ok"] is False
    assert response["kind"] == "lost"
    assert restored.session is None
    assert restored.resume_handle is None


@pytest.mark.parametrize("placement", ["inventory", "room"])
def test_duplicate_item_topology_in_checkpoint_is_rejected(tmp_path, placement):
    _, local = _paired_run(tmp_path)
    path = local._checkpoint_path(local.run_id)
    snapshot = json.loads(path.read_text(encoding="utf-8"))
    inventory = snapshot["game_state"]["player"]["inventory"]
    room_items = snapshot["game_state"]["map"]["room_items"]
    item = next(item for items in room_items.values() for item in items)
    if placement == "inventory":
        inventory.append(item)
    else:
        next(items for items in room_items.values() if item in items).append(item)
    path.write_text(json.dumps(snapshot), encoding="utf-8")

    with pytest.raises(InvalidSnapshot, match="game state is malformed"):
        LocalEngine(tmp_path / "local").adopt(local.resume_handle)


@pytest.mark.parametrize(
    ("replacement_handle", "message"),
    [
        ("not-json", "not valid JSON"),
        (
            json.dumps({"version": 1, "run_id": "", "next_turn_id": 1}),
            "malformed",
        ),
        (
            json.dumps({"version": 1, "run_id": "missing", "next_turn_id": 1}),
            "missing or corrupt",
        ),
    ],
)
def test_failed_adoption_discards_a_previously_loaded_run(
    tmp_path, replacement_handle, message
):
    _, local = _paired_run(tmp_path)
    valid_handle = local.resume_handle
    restored = LocalEngine(tmp_path / "local")
    restored.adopt(valid_handle)

    with pytest.raises(InvalidSnapshot, match=message):
        restored.adopt(replacement_handle)

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
