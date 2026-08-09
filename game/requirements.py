from __future__ import annotations

from typing import Callable, Optional


class Requirement:
    """Abstract requirement gate for exiting a room or location.

    Implementations must provide `is_met` and `denial_text`.
    """

    def is_met(self, player, world_state: dict) -> bool:  # noqa: ANN001 - dynamic player type
        raise NotImplementedError

    def denial_text(self, player, world_state: dict) -> str:  # noqa: ANN001 - dynamic player type
        return "At the threshold, your weight shifts back before you decide."


class WorldFlagTrue(Requirement):
    def __init__(self, flag_name: str, message: Optional[str] = None):
        self.flag_name = flag_name
        self._message = message

    def is_met(self, player, world_state: dict) -> bool:  # noqa: ANN001
        return bool(world_state.get(self.flag_name))

    def denial_text(self, player, world_state: dict) -> str:  # noqa: ANN001
        if self._message:
            return self._message
        return "You put your hand to it. Not yet."


class HasItem(Requirement):
    def __init__(self, item_id: str, message: Optional[str] = None):
        self.item_id = item_id
        self._message = message

    def is_met(self, player, world_state: dict) -> bool:  # noqa: ANN001
        inventory = getattr(player, "inventory", [])
        for item in inventory:
            if item == self.item_id:
                return True
            if getattr(item, "name", None) == self.item_id:
                return True
        return False

    def denial_text(self, player, world_state: dict) -> str:  # noqa: ANN001
        if self._message:
            return self._message
        return "You check both pockets. What you need is elsewhere."


class FearBelow(Requirement):
    def __init__(self, threshold: int, message: Optional[str] = None):
        self.threshold = threshold
        self._message = message

    def is_met(self, player, world_state: dict) -> bool:  # noqa: ANN001
        return getattr(player, "fear", 0) < self.threshold

    def denial_text(self, player, world_state: dict) -> str:  # noqa: ANN001
        if self._message:
            return self._message
        return "You take one step and your legs lock. Nothing moves until your breath comes back."


class CustomRequirement(Requirement):
    def __init__(
        self,
        predicate: Callable[[object, dict], bool],
        message: str,
    ) -> None:
        self.predicate = predicate
        self.message = message

    def is_met(self, player, world_state: dict) -> bool:  # noqa: ANN001
        return bool(self.predicate(player, world_state))

    def denial_text(self, player, world_state: dict) -> str:  # noqa: ANN001
        return self.message
