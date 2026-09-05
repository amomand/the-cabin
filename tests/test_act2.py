"""Tests for Act II content: anomaly logging and the Lyer encounter."""

from unittest.mock import MagicMock

import pytest

from game.actions.base import ActionContext
from game.actions.observe import ListenAction, LookAction
from game.cutscene import CutsceneManager
from game.map import Map
from game.story import AnomalyID


def _goto(m: Map, room_id: str) -> None:
    """Place the map at a room directly, failing loudly if it doesn't exist."""
    for loc in m.locations.values():
        if room_id in loc.rooms:
            m.current_location_id = loc.id
            m.current_room_id = room_id
            return
    raise AssertionError(f"room {room_id} not found")


def _fresh_map_at_first_morning() -> Map:
    m = Map()
    m.world_state.has_power = True
    m.world_state.fire_lit = True
    m.world_state.voicemail_heard = True
    m.world_state.footage_reviewed = True
    m.world_state.first_morning = True
    return m


def _walk(m: Map, route: list[str], player=None) -> None:
    """Walk a route, failing loudly if any step can't be taken."""
    for direction in route:
        moved, message = m.move(direction, player)
        assert moved, f"failed to move {direction}: {message!r}"


def _observe(m: Map, action, player=None, reply=None) -> str:
    intent = MagicMock()
    intent.reply = reply
    intent.args = {}
    result = action.execute(ActionContext(player=player, map=m, intent=intent))
    assert result.success is True
    return result.feedback


def _finish_camera(m):
    from game.story.morning import use_northern_camera
    for _ in range(3):
        result = use_northern_camera(ActionContext(player=None, map=m, intent=None), m.items["northern camera"])
        assert result.success
    assert m.world_state.camera_errand_done


class TestMorningWalk:
    def test_walk_delivers_three_tells_without_attention_and_only_then_the_encounter(self):
        m = _fresh_map_at_first_morning()
        _walk(m, ["north", "cabin"])
        moved, fox = m.move("grounds")
        assert moved and "Your fox learnt to fly" in fox
        assert m.world_state.camera_stage == "untouched"
        _finish_camera(m)
        moved, birch = m.move("north")
        assert moved and "fifty metres" in birch
        assert not m.world_state.wrongness.has(AnomalyID.HARE.value)
        moved, hare = m.move("north")
        assert moved and "no heartbeat shimmer" in hare
        moved, path = m.move("north")
        assert moved and "The forest has been emptied" in path
        assert not m.world_state.lyer_encountered
        moved, message = m.move("back")
        assert moved and message == ""  # the flight uses the cutscene channel
        assert m.world_state.lyer_encountered and m.world_state.is_wrong_layer()
        assert m.current_room_id == "cabin_main"

    @pytest.mark.parametrize("room_id, tell", [
        ("cabin_grounds_main", AnomalyID.FOX_TRACKS),
        ("deer_path", AnomalyID.HARE),
        ("old_woods", AnomalyID.STONE_FORMATIONS),
    ])
    def test_render_is_pure_and_loaded_attention_discovers_once(self, room_id, tell):
        m = _fresh_map_at_first_morning()
        m.world_state.camera_stage = "compared"
        _goto(m, room_id)
        before = m.world_state.to_dict()
        m.current_room.get_description(None, m.world_state)
        m.current_room.get_description(None, m.world_state)
        assert m.world_state.to_dict() == before
        first = _observe(m, LookAction())
        second = _observe(m, LookAction())
        assert m.world_state.wrongness.has(tell.value)
        assert m.world_state.wrongness.count() == 1
        assert first != second and second.strip()
        assert "has not moved" not in second and "still sits" not in second

    def test_backtracking_does_not_reencounter_the_hare_or_fox(self):
        m = _fresh_map_at_first_morning()
        _walk(m, ["north", "cabin", "grounds"])
        _finish_camera(m)
        _walk(m, ["north", "north", "south", "south"])
        assert m.world_state.wrongness.count() == 2
        assert "last fox print stays in your mind" in _observe(m, LookAction())
        _walk(m, ["north"])
        moved, feedback = m.move("north")
        assert moved and not feedback
        assert "do not try to find the hare again" in _observe(m, ListenAction())
        assert not m.world_state.lyer_encountered

    @pytest.mark.parametrize("room_id", ["cabin_grounds_main", "shoreline_bend"])
    @pytest.mark.parametrize("stage", ["untouched", "tested", "powered", "compared"])
    def test_both_forest_approaches_require_comparison(self, room_id, stage):
        m = _fresh_map_at_first_morning()
        m.world_state.camera_stage = stage
        _goto(m, room_id)
        moved, feedback = m.move("north")
        assert moved == (stage == "compared")
        if not moved:
            assert "camera" in feedback

    def test_evening_shore_is_open_but_the_forest_waits(self):
        m = Map()
        _walk(m, ["north", "grounds", "west", "north", "south", "east"])
        moved, feedback = m.move("north")
        assert not moved and "morning" in feedback
        assert m.world_state.wrongness.count() == 0

    def test_old_forest_save_can_retreat_to_finish_camera(self):
        m = _fresh_map_at_first_morning()
        _goto(m, "old_woods")
        _walk(m, ["south", "south", "south"])
        assert not m.world_state.lyer_encountered
        _finish_camera(m)
        _walk(m, ["north", "north", "north", "back"])
        assert m.world_state.lyer_encountered

    def test_konttori_has_no_outside_door(self):
        m = _fresh_map_at_first_morning()
        _goto(m, "konttori")
        assert not m.move("north").moved
        assert m.move("south").moved and m.current_room_id == "cabin_main"


class TestLyerEncounter:
    def test_the_flight_plays_as_a_cutscene_on_the_climax_transition(self):
        """The old_woods -> cabin_main transition names the climax and nothing
        else: old_woods has no ordinary exit reaching cabin_main, and coming
        back into the wrong cabin later is always cabin_clearing -> cabin_main.
        """
        manager = CutsceneManager()

        climax = [
            cs for cs in manager.cutscenes
            if cs.should_trigger(from_room_id="old_woods", to_room_id="cabin_main")
        ]

        assert len(climax) == 1
        prose = " ".join(climax[0].text.split())
        assert "The pine takes you at full speed." in prose
        assert "too big and too fast to be your own" in prose
        assert "You do not look." in prose
        assert "one window lit warm and yellow" in prose
        assert "throw yourself at the door." in prose

    def test_returning_to_the_wrong_cabin_does_not_replay_the_flight(self):
        manager = CutsceneManager()

        replayed = [
            cs for cs in manager.cutscenes
            if cs.should_trigger(from_room_id="cabin_clearing", to_room_id="cabin_main")
            and "The pine takes you at full speed." in cs.text
        ]

        assert replayed == []

    def test_unrelated_wrongness_cannot_substitute_for_a_forest_tell(self):
        from game.story import log_tell
        m = _fresh_map_at_first_morning()
        m.world_state.camera_stage = "compared"
        for tell in (AnomalyID.FOX_TRACKS, AnomalyID.HARE, AnomalyID.PHONE_DARK):
            log_tell(m.world_state, tell)
        _goto(m, "old_woods")
        assert m.world_state.wrongness.threshold_met(n=3)
        assert m.move("back").moved
        assert not m.world_state.lyer_encountered

    def test_encounter_only_fires_once(self):
        m = _fresh_map_at_first_morning()
        _walk(m, ["north", "cabin", "grounds"])
        _finish_camera(m)
        _walk(m, ["north", "north", "north", "back"])
        assert m.world_state.lyer_encountered
        m.world_state.reunion_stage = "complete"
        moved, message = m.move("out")
        assert not moved and "pine takes you" not in message.lower()
        assert "come inside" in message.lower()


@pytest.mark.parametrize("layer, morning, ending", [("real", False, "none"), ("wrong", True, "none"), ("real", True, "escaped")])
def test_camera_use_outside_the_errand_cannot_change_its_history(layer, morning, ending):
    from game.story.morning import use_northern_camera
    m = Map()
    _goto(m, "cabin_grounds_main")
    ws = m.world_state
    ws.world_layer, ws.first_morning, ws.ending = layer, morning, ending
    before = ws.to_dict()
    result = use_northern_camera(ActionContext(player=None, map=m, intent=None), m.items["northern camera"])
    assert result.feedback
    assert ws.to_dict() == before
