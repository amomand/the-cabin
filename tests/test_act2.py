"""Tests for Act II content: anomaly logging and the Lyer encounter."""

from game.map import Map


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


class TestAnomaliesLogOnEntry:
    def test_grounds_logs_fox_tracks_after_first_morning(self):
        m = _fresh_map_at_first_morning()
        _walk(m, ["north", "cabin", "grounds"])
        assert m.world_state.wrongness.has("fox_tracks") is True

    def test_grounds_does_not_log_before_first_morning(self):
        m = Map()
        # Skip first_morning gate.
        _walk(m, ["north", "cabin", "grounds"])
        assert m.world_state.wrongness.has("fox_tracks") is False

    def test_wood_track_logs_hare(self):
        m = _fresh_map_at_first_morning()
        _walk(m, ["north", "cabin", "grounds", "north", "north"])
        assert m.world_state.wrongness.has("hare") is True

    def test_old_woods_logs_stones(self):
        m = _fresh_map_at_first_morning()
        _walk(m, ["north", "cabin", "grounds", "north", "north", "north"])
        assert m.world_state.wrongness.has("stone_formations") is True


class TestLyerEncounter:
    def test_encounter_fires_on_leaving_old_woods_once_threshold_met(self):
        m = _fresh_map_at_first_morning()
        # Walk to old woods; three anomalies accumulate along the way.
        _walk(m, ["north", "cabin", "grounds", "north", "north", "north"])
        assert m.world_state.wrongness.threshold_met(n=3) is True
        assert m.current_room_id == "old_woods"
        assert m.world_state.is_wrong_layer() is False

        # Any attempt to leave fires the encounter.
        moved, message = m.move("south", player=None)

        assert moved is True
        assert m.world_state.lyer_encountered is True
        assert m.world_state.is_wrong_layer() is True
        assert m.current_room_id == "cabin_main"
        assert "tree" in message.lower()

    def test_encounter_does_not_fire_without_threshold(self):
        m = _fresh_map_at_first_morning()
        # Reach old woods but manipulate wrongness so threshold not met.
        _walk(m, ["north", "cabin", "grounds", "north", "north", "north"])
        # Strip entries down to below threshold.
        m.world_state.wrongness.entries = m.world_state.wrongness.entries[:2]
        assert m.world_state.wrongness.threshold_met(n=3) is False

        moved, _ = m.move("south", player=None)
        assert moved is True
        assert m.world_state.lyer_encountered is False
        assert m.world_state.is_wrong_layer() is False

    def test_encounter_only_fires_once(self):
        m = _fresh_map_at_first_morning()
        _walk(m, ["north", "cabin", "grounds", "north", "north", "north"])
        m.move("south", player=None)
        assert m.world_state.lyer_encountered is True

        # Already flipped to wrong layer; subsequent moves behave normally.
        moved, message = m.move("out", player=None)
        assert moved is True
        assert "tree" not in message.lower()
