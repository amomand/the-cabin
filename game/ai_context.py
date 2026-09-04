"""Helpers for building AI interpreter context."""

from __future__ import annotations

from typing import Protocol


WRONG_LAYER_ONLY_ROOM_ITEMS = {"nika", "mattress", "tins"}


class _RoomLike(Protocol):
    items: list


class _WorldStateLike(Protocol):
    def is_wrong_layer(self) -> bool:
        ...


def _visible_in_layer(room: _RoomLike, world_state: _WorldStateLike) -> list:
    """Return the item objects the current layer allows the AI to see."""
    if world_state.is_wrong_layer():
        return list(room.items)

    return [
        item
        for item in room.items
        if str(item.name).strip().lower() not in WRONG_LAYER_ONLY_ROOM_ITEMS
    ]


def visible_room_item_names(room: _RoomLike, world_state: _WorldStateLike) -> list[str]:
    """Return item names the AI may treat as present in the current layer."""
    return [item.name for item in _visible_in_layer(room, world_state)]


def carryable_room_item_names(room: _RoomLike, world_state: _WorldStateLike) -> list[str]:
    """Return the visible item names that can actually be picked up.

    The rule-based take branch gates on this rather than on presence. A
    fireplace, a bed, a window and Nika are all present; none of them can be
    lifted, and answering an attempt with the inventory machinery is the bug
    this list exists to close.
    """
    return [
        item.name
        for item in _visible_in_layer(room, world_state)
        if item.is_carryable()
    ]


def build_ai_context(player, game_map, quest_manager) -> dict:
    """Build the context payload sent to the AI interpreter.

    Single source of truth shared by GameEngine and the model evaluation
    harness (which derives scenario contexts from dev save seeds).
    """
    from game.ai_interpreter import ALLOWED_ACTIONS
    from game.story import can_advance_to_dawn, is_dawn_offer_active

    room = game_map.current_room
    world_state = game_map.world_state
    return {
        "room_name": room.display_name(world_state),
        "room_id": room.id,
        "exits": list(room.effective_exits(world_state).keys()),
        "room_items": visible_room_item_names(room, world_state),
        "carryable_room_items": carryable_room_item_names(room, world_state),
        "inventory": player.get_inventory_names(),
        "equipment": ["phone", "camera feed"],
        "world_flags": world_state.to_dict(),
        "can_advance_to_dawn": can_advance_to_dawn(world_state, room.id),
        "is_dawn_offer_active": is_dawn_offer_active(world_state, room.id),
        # Sorted: ALLOWED_ACTIONS is a set, and list(set) ordering varies by
        # PYTHONHASHSEED. A stable order keeps the prompt payload reproducible
        # (and prompt-cache-friendly) across processes.
        "allowed_actions": sorted(ALLOWED_ACTIONS),
        "fear": player.fear,
        "health": player.health,
        "rooms_visited": len(game_map.visited_rooms),
        "been_here_before": game_map.current_room_been_here_before,
        "active_quest": (
            quest_manager.active_quest.objective
            if quest_manager.has_active_quest() else None
        ),
    }
