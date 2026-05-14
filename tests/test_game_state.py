"""Tests for GameState serialization round-trip."""
from __future__ import annotations

from game.cutscene import Cutscene, CutsceneManager
from game.game_state import GameState
from game.map import Map
from game.player import Player
from game.quests import create_quest_manager


def _make_state() -> GameState:
    return GameState(
        player=Player(),
        map=Map(),
        quest_manager=create_quest_manager(),
        cutscene_manager=CutsceneManager(),
    )


def _fresh_managers():
    return {
        "player": Player(),
        "map": Map(),
        "quest_manager": create_quest_manager(),
        "cutscene_manager": CutsceneManager(),
    }


def test_played_cutscenes_round_trip_through_save_load() -> None:
    """A cutscene marked has_played in one run must stay played after load.

    Regression: GameState.to_dict wrote cutscenes.played_ids but from_dict
    never read them, so authored cutscenes could re-fire after `load`.
    """
    state = _make_state()
    assert state.cutscene_manager.cutscenes, "expected at least one cutscene to exist"

    target = state.cutscene_manager.cutscenes[0]
    target.has_played = True
    expected_id = target.text[:50]

    data = state.to_dict()
    assert expected_id in data["cutscenes"]["played_ids"]

    managers = _fresh_managers()
    # Sanity: a fresh CutsceneManager starts with nothing played.
    assert not any(cs.has_played for cs in managers["cutscene_manager"].cutscenes)

    restored = GameState.from_dict(data, **managers)

    restored_target = next(
        cs for cs in restored.cutscene_manager.cutscenes if cs.text[:50] == expected_id
    )
    assert restored_target.has_played, (
        "loaded save should preserve cutscene play state so authored beats "
        "do not re-fire on the next trigger"
    )


def test_unplayed_cutscenes_stay_unplayed_after_round_trip() -> None:
    """Cutscenes that never played should remain unplayed after load."""
    state = _make_state()

    data = state.to_dict()
    assert data["cutscenes"]["played_ids"] == []

    restored = GameState.from_dict(data, **_fresh_managers())
    assert not any(cs.has_played for cs in restored.cutscene_manager.cutscenes)


def test_set_played_ids_restores_matching_cutscenes() -> None:
    """CutsceneManager.set_played_ids marks only matching cutscenes."""
    manager = CutsceneManager()
    manager.add_cutscene(Cutscene("AAAA second cutscene text body"))
    assert len(manager.cutscenes) >= 2

    target_id = manager.cutscenes[1].text[:50]
    manager.set_played_ids([target_id])

    assert manager.cutscenes[1].has_played
    assert not manager.cutscenes[0].has_played


def test_set_played_ids_clears_non_matching_cutscenes() -> None:
    """set_played_ids is authoritative: cutscenes not in the saved set get
    has_played reset to False, even if they were already marked played.

    This guards the load-into-existing-manager case: ``GameEngine._load_game``
    calls ``GameState.from_dict`` on the engine's already-instantiated
    ``CutsceneManager``, so loading an older save must not leave cutscenes
    from the current run marked as played.
    """
    manager = CutsceneManager()
    manager.add_cutscene(Cutscene("AAAA second cutscene text body"))
    assert len(manager.cutscenes) >= 2

    # Pre-mark the first cutscene as played (the "current run" state).
    manager.cutscenes[0].has_played = True

    # Restore from a saved set that only includes the second cutscene.
    target_id = manager.cutscenes[1].text[:50]
    manager.set_played_ids([target_id])

    # First should now be cleared; second should be set.
    assert not manager.cutscenes[0].has_played
    assert manager.cutscenes[1].has_played
