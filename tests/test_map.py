"""Tests for map visit tracking and display."""

import ast
import inspect
import textwrap

from game.map import Map


def _display_map_room_ids() -> tuple[set[str], set[str]]:
    """Return room IDs hard-coded into Map.display_map's layout references."""
    source = textwrap.dedent(inspect.getsource(Map.display_map))
    tree = ast.parse(source)
    references: set[str] = set()
    rendered: set[str] = set()

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
            continue

        if node.func.id == "visited":
            args = node.args[:1]
            target = rendered
        elif node.func.id == "connected":
            args = node.args[:2]
            target = references
        else:
            continue

        for arg in args:
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                references.add(arg.value)
                target.add(arg.value)

    return references, rendered


def _real_reachable_room_ids(map_) -> set[str]:
    """Return rooms reachable from the starting room through real-layer exits."""
    rooms = {
        room_id: room
        for location in map_.locations.values()
        for room_id, room in location.rooms.items()
    }
    visited = {map_.current_room_id}
    frontier = [map_.current_room_id]

    while frontier:
        room_id = frontier.pop()
        for _, target_room_id in rooms[room_id].exits.values():
            if target_room_id not in visited:
                visited.add(target_room_id)
                frontier.append(target_room_id)

    return visited


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

    def test_display_map_renders_bent_forest_route(self, sample_map):
        """The discovered forest bends instead of rendering as a ladder."""
        visited_rooms = {
            "wilderness_start",
            "cabin_clearing",
            "cabin_main",
            "konttori",
            "bedroom",
            "cabin_grounds_main",
            "sauna",
            "lakeside",
            "frozen_inlet",
            "shoreline_bend",
            "wood_track",
            "deer_path",
            "old_woods",
        }

        assert sample_map.display_map(visited_rooms) == "\n".join(
            [
                "                            Deer Path",
                "                                |",
                "                 Old Woods - Wood Track",
                "                                |",
                "                Frozen Inlet    |",
                "                     |          |",
                "          Sauna",
                "          |",
                "Cabin Grounds - Lakeside - Shoreline Bend",
                "     ||",
                "  Konttori",
                "     ||",
                " The Cabin - Bedroom",
                "     |",
                "The Clearing",
                "     |",
                "The Wilderness",
            ]
        )

    def test_display_map_places_new_northern_room_above_start(self, sample_map):
        """Early exploration still reads north-to-south."""
        visited_rooms = {"wilderness_start", "cabin_clearing"}

        assert sample_map.display_map(visited_rooms) == "\n".join(
            [
                "The Clearing",
                "     |",
                "The Wilderness",
            ]
        )

    def test_display_map_shows_dead_end_only_after_discovery(self, sample_map):
        """Unvisited dead ends are not spoiled by the map."""
        visited_rooms = {
            "cabin_grounds_main",
            "lakeside",
            "shoreline_bend",
        }

        assert sample_map.display_map(visited_rooms) == "\n".join(
            [
                "Cabin Grounds - Lakeside - Shoreline Bend",
            ]
        )

        visited_rooms.add("frozen_inlet")

        assert sample_map.display_map(visited_rooms) == "\n".join(
            [
                "                Frozen Inlet",
                "                     |",
                "Cabin Grounds - Lakeside - Shoreline Bend",
            ]
        )

    def test_display_map_layout_references_match_real_room_graph(self, sample_map):
        """The hand-authored layout cannot drift from the canonical room graph."""
        room_ids = {
            room_id
            for location in sample_map.locations.values()
            for room_id in location.rooms
        }
        referenced_room_ids, rendered_room_ids = _display_map_room_ids()

        assert referenced_room_ids <= room_ids
        assert _real_reachable_room_ids(sample_map) <= rendered_room_ids
