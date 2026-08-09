"""Tests for Act II content: anomaly logging and the Lyer encounter."""

from unittest.mock import MagicMock

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


ACT_II_ROUTE = ["north", "cabin", "grounds", "north", "east", "north", "west"]


def _observe(m: Map, action, player=None, reply=None) -> str:
    intent = MagicMock()
    intent.reply = reply
    intent.args = {}
    result = action.execute(ActionContext(player=player, map=m, intent=intent))
    assert result.success is True
    return result.feedback


class TestAnomaliesGateOnAttention:
    def test_grounds_does_not_log_on_entry_after_first_morning(self):
        m = _fresh_map_at_first_morning()
        _walk(m, ["north", "cabin", "grounds"])
        assert m.world_state.wrongness.has(AnomalyID.FOX_TRACKS.value) is False

    def test_grounds_logs_fox_tracks_on_look_after_first_morning(self):
        m = _fresh_map_at_first_morning()
        _walk(m, ["north", "cabin", "grounds"])

        feedback = _observe(m, LookAction())

        assert m.world_state.wrongness.has(AnomalyID.FOX_TRACKS.value) is True
        assert "The last print is perfect" in feedback
        assert "Your fox learnt to fly" in feedback
        assert "reads full, but the camera is dead" in feedback
        assert "forked birch" in feedback

    def test_grounds_does_not_log_before_first_morning(self):
        m = Map()
        # Skip first_morning gate.
        _walk(m, ["north", "cabin", "grounds"])
        _observe(m, LookAction())
        assert m.world_state.wrongness.has(AnomalyID.FOX_TRACKS.value) is False

    def test_wood_track_does_not_log_on_entry(self):
        m = _fresh_map_at_first_morning()
        _walk(m, ["north", "cabin", "grounds", "north", "east", "north"])
        assert m.world_state.wrongness.has(AnomalyID.HARE.value) is False
        description = m.current_room.get_description(None, m.world_state)
        assert "forked birch grows from unbroken ground" in description
        assert "Two hundred metres of young spruce should not have closed" in description

    def test_wood_track_logs_hare_on_look(self):
        m = _fresh_map_at_first_morning()
        _walk(m, ["north", "cabin", "grounds", "north", "east", "north"])

        feedback = _observe(m, LookAction())

        assert m.world_state.wrongness.has(AnomalyID.HARE.value) is True
        assert "hare sits" in feedback

    def test_wood_track_logs_hare_on_listen(self):
        m = _fresh_map_at_first_morning()
        _walk(m, ["north", "cabin", "grounds", "north", "east", "north"])

        feedback = _observe(m, ListenAction())

        assert m.world_state.wrongness.has(AnomalyID.HARE.value) is True
        assert "does not breathe" in feedback

    def test_old_woods_does_not_log_on_entry(self):
        m = _fresh_map_at_first_morning()
        _walk(m, ACT_II_ROUTE)
        assert m.world_state.wrongness.has(AnomalyID.STONE_FORMATIONS.value) is False

    def test_old_woods_logs_missing_path_on_look(self):
        m = _fresh_map_at_first_morning()
        _walk(m, ACT_II_ROUTE)

        feedback = _observe(m, LookAction())

        assert m.world_state.wrongness.has(AnomalyID.STONE_FORMATIONS.value) is True
        assert "deer path is not there" in feedback
        assert "stone formations" not in feedback

    def test_repeated_attention_does_not_duplicate_tells(self):
        m = _fresh_map_at_first_morning()
        _walk(m, ["north", "cabin", "grounds", "north", "east", "north"])

        _observe(m, LookAction())
        _observe(m, ListenAction())
        _observe(m, LookAction())

        assert m.world_state.wrongness.count() == 1
        assert m.world_state.wrongness.has(AnomalyID.HARE.value) is True


class TestActIIForestShape:
    def test_go_north_spam_reaches_dead_end_not_old_woods(self):
        m = _fresh_map_at_first_morning()

        _walk(m, ["north", "cabin", "grounds", "north", "north"])
        moved, message = m.move("north", player=None)

        assert moved is False
        assert m.current_room_id == "frozen_inlet"
        assert "trees and dark" in message.lower()

    def test_required_route_bends_to_old_woods(self):
        m = _fresh_map_at_first_morning()

        _walk(m, ACT_II_ROUTE)

        assert m.current_room_id == "old_woods"

    def test_frozen_inlet_is_dead_end_with_clear_return(self):
        m = _fresh_map_at_first_morning()
        _walk(m, ["north", "cabin", "grounds", "north", "north"])

        moved, _ = m.move("south", player=None)

        assert moved is True
        assert m.current_room_id == "lakeside"

    def test_birch_thicket_is_dead_end_with_clear_return(self):
        m = _fresh_map_at_first_morning()
        _walk(m, ["north", "cabin", "grounds", "north", "east", "north", "north"])

        moved, _ = m.move("south", player=None)

        assert moved is True
        assert m.current_room_id == "wood_track"


class TestLyerEncounter:
    def test_encounter_fires_on_leaving_old_woods_once_threshold_met(self):
        m = _fresh_map_at_first_morning()
        _walk(m, ["north", "cabin", "grounds"])
        _observe(m, LookAction())
        _walk(m, ["north", "east", "north"])
        _observe(m, LookAction())
        _walk(m, ["west"])
        _observe(m, LookAction())
        assert m.world_state.wrongness.threshold_met(n=3) is True
        assert m.current_room_id == "old_woods"
        assert m.world_state.is_wrong_layer() is False

        # Any attempt to leave fires the encounter.
        moved, message = m.move("east", player=None)

        assert moved is True
        assert m.world_state.lyer_encountered is True
        assert m.world_state.is_wrong_layer() is True
        assert m.current_room_id == "cabin_main"
        # The flight is not returned as feedback. Both surfaces render feedback
        # after the destination room, which printed the arrival before the run
        # that caused it (#187). It plays through the cutscene channel instead.
        assert message == ""

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
        assert "The pine takes you at full speed." in climax[0].text
        assert "too big and too fast to be your own" in climax[0].text
        assert "You do not look." in climax[0].text
        assert "one window lit warm and yellow" in climax[0].text
        assert "throw yourself at the door." in climax[0].text

    def test_returning_to_the_wrong_cabin_does_not_replay_the_flight(self):
        manager = CutsceneManager()

        replayed = [
            cs for cs in manager.cutscenes
            if cs.should_trigger(from_room_id="cabin_clearing", to_room_id="cabin_main")
            and "The pine takes you at full speed." in cs.text
        ]

        assert replayed == []

    def test_encounter_does_not_fire_without_threshold(self):
        m = _fresh_map_at_first_morning()
        _walk(m, ACT_II_ROUTE)
        assert m.world_state.wrongness.threshold_met(n=3) is False

        moved, _ = m.move("east", player=None)
        assert moved is True
        assert m.world_state.lyer_encountered is False
        assert m.world_state.is_wrong_layer() is False

    def test_encounter_only_fires_once(self):
        m = _fresh_map_at_first_morning()
        _walk(m, ["north", "cabin", "grounds"])
        _observe(m, LookAction())
        _walk(m, ["north", "east", "north"])
        _observe(m, LookAction())
        _walk(m, ["west"])
        _observe(m, LookAction())
        m.move("east", player=None)
        assert m.world_state.lyer_encountered is True

        # Already flipped to wrong layer; the consent-door beat now holds the
        # first "out" after the reunion lands (rewritten canon, #141).
        m.world_state.reunion_stage = "complete"
        moved, message = m.move("out", player=None)
        assert moved is False
        # Encounter-specific narration ("the pine takes you") must not
        # re-fire. The consent beat narrates the wrong outside, which is fine.
        assert "pine takes you" not in message.lower()
        assert "come inside" in message.lower()
