"""Tests for map visit tracking."""


class TestMapVisitTracking:
    """Tests for per-room revisit state."""

    def test_current_room_been_here_before_is_false_on_first_entry(self, sample_map, sample_player):
        """A newly entered room is not treated as a revisit."""
        assert sample_map.current_room_been_here_before is False

        moved, _ = sample_map.move("north", sample_player)

        assert moved is True
        assert sample_map.current_room.id == "cabin_clearing"
        assert sample_map.current_room_been_here_before is False

    def test_current_room_been_here_before_is_true_on_return(self, sample_map, sample_player):
        """Returning to a room flips the revisit flag."""
        sample_map.move("north", sample_player)

        moved, _ = sample_map.move("south", sample_player)

        assert moved is True
        assert sample_map.current_room.id == "wilderness_start"
        assert sample_map.current_room_been_here_before is True
