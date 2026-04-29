"""Tests for the dev seed-save tool: each seed must round-trip through SaveManager."""
from __future__ import annotations

from pathlib import Path

import pytest

from game.cutscene import CutsceneManager
from game.devtools import seed_saves
from game.game_state import GameState
from game.map import Map
from game.persistence import SaveManager
from game.player import Player
from game.quests import create_quest_manager


def _load_roundtrip(tmp_path: Path, state: GameState, slot: str) -> GameState:
    manager = SaveManager(save_dir=tmp_path)
    manager.save_game(state, slot_name=slot)
    raw = manager.load_game(slot)
    assert raw is not None
    return GameState.from_dict(
        raw,
        player=Player(),
        map=Map(),
        quest_manager=create_quest_manager(),
        cutscene_manager=CutsceneManager(),
    )


@pytest.mark.parametrize("name", list(seed_saves.SEEDS.keys()))
def test_seed_builds_and_round_trips(tmp_path: Path, name: str) -> None:
    state = seed_saves.SEEDS[name]()
    restored = _load_roundtrip(tmp_path, state, name)

    # Room and layer survived the round-trip.
    assert restored.map.current_room.id == state.map.current_room.id
    assert restored.world_state.world_layer == state.world_state.world_layer
    assert restored.world_state.reunion_stage == state.world_state.reunion_stage
    assert restored.world_state.recognition == state.world_state.recognition
    assert restored.world_state.wrongness.count() == state.world_state.wrongness.count()
    assert restored.quest_manager.completed_quests == state.quest_manager.completed_quests


def test_act1_end_has_act1_flags() -> None:
    state = seed_saves.seed_act1_end()
    ws = state.world_state
    assert ws.has_power and ws.fire_lit and ws.first_morning
    assert ws.sauna_used and ws.voicemail_heard and ws.footage_reviewed
    assert "warm_up" in state.quest_manager.completed_quests


def test_act2_mid_below_threshold() -> None:
    ws = seed_saves.seed_act2_mid().world_state
    assert ws.wrongness.count() == 2
    assert not ws.wrongness.threshold_met()
    assert ws.world_layer == "real"


def test_act3_arrival_is_in_wrong_layer_with_reunion_started() -> None:
    state = seed_saves.seed_act3_arrival()
    ws = state.world_state
    assert ws.world_layer == "wrong"
    assert ws.reunion_stage == "arrival"
    assert ws.lyer_encountered
    assert ws.wrongness.threshold_met()
    assert state.map.current_room.id == "cabin_main"


def test_act4_recognition_unlocks_refusal() -> None:
    state = seed_saves.seed_act4_recognition()
    ws = state.world_state
    assert ws.recognition
    assert ws.reunion_stage == "complete"
    assert ws.world_layer == "wrong"
    assert ws.wrong_outside_seen
    assert ws.wrongness.has("correction_turn")


def test_generate_all_writes_files(tmp_path: Path) -> None:
    paths = seed_saves.generate_all(save_dir=tmp_path)
    assert len(paths) == len(seed_saves.SEEDS)
    for p in paths:
        assert p.exists()


def test_use_seed_copies_into_main_saves(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dev_dir = tmp_path / "dev"
    main_dir = tmp_path / "main"
    monkeypatch.setattr(seed_saves, "DEV_SAVE_DIR", dev_dir)
    monkeypatch.setattr(seed_saves, "MAIN_SAVE_DIR", main_dir)
    seed_saves.generate_all(save_dir=dev_dir)

    dst = seed_saves.use_seed("act3_arrival")
    assert dst == main_dir / "act3_arrival.json"
    assert dst.exists()
