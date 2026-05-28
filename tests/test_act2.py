"""Tests for Act II content: anomaly logging and the Lyer encounter."""

from unittest.mock import MagicMock

from game.actions.base import ActionContext
from game.actions.observe import ListenAction, LookAction
from game.map import Map
from game.story import AnomalyID


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
        assert "line of fox tracks crosses" in feedback

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

    def test_old_woods_logs_stones_on_look(self):
        m = _fresh_map_at_first_morning()
        _walk(m, ACT_II_ROUTE)

        feedback = _observe(m, LookAction())

        assert m.world_state.wrongness.has(AnomalyID.STONE_FORMATIONS.value) is True
        assert "stone formations" in feedback

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

    def test_deer_path_is_dead_end_with_clear_return(self):
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
        assert "tree" in message.lower()

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

        # Already flipped to wrong layer; subsequent moves behave normally.
        # The reunion must land before Elli can leave the wrong cabin.
        m.world_state.reunion_stage = "complete"
        moved, message = m.move("out", player=None)
        assert moved is True
        # Encounter-specific narration ("you hit the tree full on") must not
        # re-fire. The wrong-outside beat narrates a treeline, which is fine.
        assert "tree full on" not in message.lower()
