from __future__ import annotations

from typing import Callable, Dict, List, Optional, Tuple

from game.requirements import Requirement


class Room:
    """A room within a location.

    - `exits` map direction string to a tuple of `(target_location_id, target_room_id)`.
      This is room-level routing and may cross location boundaries.
    - `exit_criteria` are checked before leaving this room via any exit.
    - `get_description` can procedurally compose text from player and world state.
    """

    def __init__(
        self,
        name: str,
        description: str,
        *,
        room_id: Optional[str] = None,
        exit_criteria: Optional[List[Requirement]] = None,
        description_fn: Optional[Callable[[object, dict, str], str]] = None,
    ) -> None:
        self.id = room_id or name.lower().replace(" ", "_")
        self.name = name
        self.static_description = description
        # exits: direction -> (location_id, room_id)
        self.exits: Dict[str, Tuple[str, str]] = {}
        self.exit_criteria = exit_criteria or []
        # Optional override: function(player, world_state, base_text) -> str
        self._description_fn = description_fn

    # Backward-compat convenience
    @property
    def description(self) -> str:  # type: ignore[override]
        return self.static_description

    @description.setter
    def description(self, value: str) -> None:
        self.static_description = value

    def get_description(self, player, world_state: dict) -> str:  # noqa: ANN001
        base = self.static_description
        if self._description_fn is not None:
            return self._description_fn(player, world_state, base)
        return base

    def on_enter(self, player, world_state: dict) -> None:  # noqa: ANN001
        # Hook for one-time triggers or ambient effects
        return