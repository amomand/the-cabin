"""Tests for map visit tracking and display."""


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

    def test_clearing_allows_northward_progression_to_cabin(self, sample_map, sample_player):
        """The early route keeps north aligned with forward progress."""
        sample_map.move("north", sample_player)

        moved, _ = sample_map.move("north", sample_player)

        assert moved is True
        assert sample_map.current_room.id == "cabin_main"


class TestMapDisplay:
    """Tests for the ASCII map display."""

    def test_display_map_places_north_at_top(self, sample_map):
        """The furthest-north room renders above the southern start."""
        visited_rooms = {
            "wilderness_start",
            "cabin_clearing",
            "cabin_main",
            "konttori",
            "cabin_grounds_main",
            "lakeside",
            "wood_track",
            "old_woods",
        }

        assert sample_map.display_map(visited_rooms) == "\n".join(
            [
                "Old Woods",
                " |",
                "Wood Track",
                " |",
                "Lakeside",
                " |",
                "Cabin Grounds",
                "||",
                "Konttori",
                "||",
                "The Cabin",
                " |",
                "The Clearing",
                " |",
                "The Wilderness",
            ]
        )

    def test_display_map_places_new_northern_room_above_start(self, sample_map):
        """Early exploration still reads north-to-south."""
        visited_rooms = {"wilderness_start", "cabin_clearing"}

        assert sample_map.display_map(visited_rooms) == "\n".join(
            [
                "The Clearing",
                " |",
                "The Wilderness",
            ]
        )
