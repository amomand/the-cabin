"""Helpers for building AI interpreter context."""

from __future__ import annotations

from typing import Protocol


WRONG_LAYER_ONLY_ROOM_ITEMS = {"window", "mug", "nika"}


class _RoomLike(Protocol):
    items: list


class _WorldStateLike(Protocol):
    def is_wrong_layer(self) -> bool:
        ...


def visible_room_item_names(room: _RoomLike, world_state: _WorldStateLike) -> list[str]:
    """Return item names the AI may treat as present in the current layer."""
    names = [item.name for item in room.items]
    if world_state.is_wrong_layer():
        return names

    return [
        name
        for name in names
        if name.strip().lower() not in WRONG_LAYER_ONLY_ROOM_ITEMS
    ]
