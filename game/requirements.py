from __future__ import annotations

from typing import Callable, Optional


class Requirement:
    """Abstract requirement gate for exiting a room or location.

    Implementations must provide `is_met` and `denial_text`.
    """

    def is_met(self, player, world_state: dict) -> bool:  # noqa: ANN001 - dynamic player type
        raise NotImplementedError

    def denial_text(self, player, world_state: dict) -> str:  # noqa: ANN001 - dynamic player type
        return "You stall at the threshold. Something holds you back."


class WorldFlagTrue(Requirement):
    def __init__(self, flag_name: str, message: Optional[str] = None):
        self.flag_name = flag_name
        self._message = message

    def is_met(self, player, world_state: dict) -> bool:  # noqa: ANN001
        return bool(world_state.get(self.flag_name))

    def denial_text(self, player, world_state: dict) -> str:  # noqa: ANN001
        if self._message:
            return self._message
        return "You try, but it doesn't give. Something essential isn't in place yet."


class HasItem(Requirement):
    def __init__(self, item_id: str, message: Optional[str] = None):
        self.item_id = item_id
        self._message = message

    def is_met(self, player, world_state: dict) -> bool:  # noqa: ANN001
        return self.item_id in getattr(player, "inventory", [])

    def denial_text(self, player, world_state: dict) -> str:  # noqa: ANN001
        if self._message:
            return self._message
        return "You pat your pockets. Empty. Not like this."


class FearBelow(Requirement):
    def __init__(self, threshold: int, message: Optional[str] = None):
        self.threshold = threshold
        self._message = message

    def is_met(self, player, world_state: dict) -> bool:  # noqa: ANN001
        return getattr(player, "fear", 0) < self.threshold

    def denial_text(self, player, world_state: dict) -> str:  # noqa: ANN001
        if self._message:
            return self._message
        return "Your nerves spike. Your feet won't move. You breathe, but it doesn't help."


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


