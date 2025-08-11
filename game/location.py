from __future__ import annotations

from typing import Callable, Dict, List, Optional, Tuple

from game.requirements import Requirement


class Location:
    """A higher-level container of rooms.

    Transitions between locations should still occur via room exits, but
    location-level `exit_criteria` can optionally gate leaving the location
    entirely (use sparingly).
    """

    def __init__(
        self,
        location_id: str,
        name: str,
        overview_description: str | Callable[[dict], str],
        *,
        exit_criteria: Optional[List[Requirement]] = None,
    ) -> None:
        self.id = location_id
        self.name = name
        self.overview_description = overview_description
        self.rooms: Dict[str, "Room"] = {}
        self.exits: Dict[str, str] = {}
        self.exit_criteria = exit_criteria or []

    def add_room(self, room: "Room") -> None:
        self.rooms[room.id] = room

    def get_overview_text(self, world_state: dict) -> str:
        if callable(self.overview_description):
            return self.overview_description(world_state)
        return self.overview_description


