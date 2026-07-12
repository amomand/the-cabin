"""Helpers for building AI interpreter context."""

from __future__ import annotations

from typing import Protocol


WRONG_LAYER_ONLY_ROOM_ITEMS = {"window", "mug", "nika"}


class _RoomLike(Protocol):
    items: list
    wildlife: list


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


def visible_room_wildlife_names(room: _RoomLike, world_state: _WorldStateLike) -> list[str]:
    """Return wildlife names the AI may treat as present in the current layer.

    The wrong layer holds nothing that lives; the model must not be told
    otherwise while the authored prose says the forest is empty.
    """
    if world_state.is_wrong_layer():
        return []
    return [animal.name for animal in room.wildlife]


def build_ai_context(player, game_map, quest_manager) -> dict:
    """Build the context payload sent to the AI interpreter.

    Single source of truth shared by GameEngine and the model evaluation
    harness (which derives scenario contexts from dev save seeds).
    """
    from game.ai_interpreter import ALLOWED_ACTIONS

    room = game_map.current_room
    return {
        "room_name": room.name,
        "room_id": room.id,
        "exits": list(room.effective_exits(game_map.world_state).keys()),
        "room_items": visible_room_item_names(room, game_map.world_state),
        "room_wildlife": visible_room_wildlife_names(room, game_map.world_state),
        "inventory": player.get_inventory_names(),
        "world_flags": game_map.world_state.to_dict(),
        "allowed_actions": list(ALLOWED_ACTIONS),
        "fear": player.fear,
        "health": player.health,
        "rooms_visited": len(game_map.visited_rooms),
        "been_here_before": game_map.current_room_been_here_before,
        "active_quest": (
            quest_manager.active_quest.objective
            if quest_manager.has_active_quest() else None
        ),
    }
