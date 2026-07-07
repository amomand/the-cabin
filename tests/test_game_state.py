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


def _room(m: Map, room_id: str):
    for location in m.locations.values():
        if room_id in location.rooms:
            return location.rooms[room_id]
    raise AssertionError(f"room {room_id} not found")


class TestItemPlacementRoundTrip:
    """Regression tests for issue #111: item duplication after load."""

    def test_taken_item_does_not_duplicate_after_load(self):
        state = _make_state()
        cabin = _room(state.map, "cabin_main")
        matches = cabin.remove_item("matches")
        assert matches is not None
        state.player.add_item(matches)

        restored = GameState.from_dict(state.to_dict(), **_fresh_managers())

        assert restored.player.has_item("matches")
        assert not _room(restored.map, "cabin_main").has_item("matches")

    def test_dropped_item_stays_where_dropped(self):
        state = _make_state()
        cabin = _room(state.map, "cabin_main")
        matches = cabin.remove_item("matches")
        _room(state.map, "wilderness_start").add_item(matches)

        restored = GameState.from_dict(state.to_dict(), **_fresh_managers())

        assert not restored.player.has_item("matches")
        assert _room(restored.map, "wilderness_start").has_item("matches")
        assert not _room(restored.map, "cabin_main").has_item("matches")

    def test_legacy_save_without_room_items_strips_inventory_from_rooms(self):
        state = _make_state()
        cabin = _room(state.map, "cabin_main")
        state.player.add_item(cabin.remove_item("matches"))

        data = state.to_dict()
        del data["map"]["room_items"]

        restored = GameState.from_dict(data, **_fresh_managers())

        assert restored.player.has_item("matches")
        assert not _room(restored.map, "cabin_main").has_item("matches")


class TestQuestStatusRoundTrip:
    """Regression tests for issue #111: quest status lost on load."""

    def test_active_quest_stays_active_and_still_updates(self):
        from game.quest import QuestStatus

        state = _make_state()
        warm_up = state.quest_manager.quests["warm_up"]
        state.quest_manager.activate_quest(warm_up)

        restored = GameState.from_dict(state.to_dict(), **_fresh_managers())

        quest = restored.quest_manager.quests["warm_up"]
        assert quest.status is QuestStatus.ACTIVE
        assert restored.quest_manager.active_quest is quest

        update = restored.quest_manager.check_updates(
            "fuel_gathered", {"action": "take_firewood"}, restored.player, {}
        )
        assert update == "You now have firewood to burn."

    def test_completed_quest_does_not_retrigger(self):
        from game.quest import QuestStatus

        state = _make_state()
        warm_up = state.quest_manager.quests["warm_up"]
        state.quest_manager.activate_quest(warm_up)
        warm_up.status = QuestStatus.COMPLETED
        state.quest_manager.completed_quests = ["warm_up"]
        state.quest_manager.active_quest = None

        restored = GameState.from_dict(state.to_dict(), **_fresh_managers())

        assert restored.quest_manager.quests["warm_up"].status is QuestStatus.COMPLETED
        triggered = restored.quest_manager.check_triggers(
            "location", {"room_id": "lakeside"}, restored.player, {}
        )
        assert triggered is None

    def test_quest_updates_survive_load(self):
        state = _make_state()
        warm_up = state.quest_manager.quests["warm_up"]
        state.quest_manager.activate_quest(warm_up)
        warm_up.add_update("power_restored", "Power hums through the cabin.", 1.0)

        restored = GameState.from_dict(state.to_dict(), **_fresh_managers())

        display = restored.quest_manager.get_active_quest_display()
        assert "Power hums through the cabin." in display

    def test_stale_manager_state_is_reset_on_load(self):
        """Loading into an already-running manager must clear current-run status."""
        from game.quest import QuestStatus

        state = _make_state()  # nothing active in the save
        data = state.to_dict()

        managers = _fresh_managers()
        live = managers["quest_manager"]
        live.activate_quest(live.quests["warm_up"])  # current-run state

        restored = GameState.from_dict(data, **managers)

        assert restored.quest_manager.quests["warm_up"].status is QuestStatus.INACTIVE
        assert restored.quest_manager.active_quest is None
