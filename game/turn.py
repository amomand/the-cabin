"""Surface-agnostic turn core shared by the terminal and web surfaces.

`GameEngine` and `WebGameSession` both run a player's command through
`take_turn`. Everything a turn *decides* lives here: how input is interpreted,
which action runs, which effects land, which events fire, and what the player
is told. Only transport and rendering stay per-surface.

This follows the `game.death` pattern. The decision is shared so the two
surfaces cannot answer the same input differently; the render path is not,
because a terminal prints and a web session builds frames.

Feedback is written through a `set_feedback` callback rather than returned,
because quest and cutscene listeners fire *during* event handling and are
expected to replace the action's own feedback with their narration. Returning
a value would let the caller overwrite whatever a listener had just set.
"""

from __future__ import annotations

from typing import Callable

from game.ai_context import build_ai_context
from game.ai_interpreter import interpret
from game.events.types import (
    PlayerMovedEvent, ItemTakenEvent, ItemDroppedEvent, ItemThrownEvent,
    PowerRestoredEvent, FireLitEvent, FireAttemptEvent,
    LightSwitchUsedEvent, FireplaceUsedEvent, FuelGatheredEvent,
)


# Narrated fallback when the registry has no action for the interpreted intent
# and the model offered no reply of its own.
UNKNOWN_ACTION_FEEDBACK = (
    "You start, then think better of it. The cold in your chest makes you careful."
)

# Bounds on a single turn's AI-proposed deltas.
MAX_EFFECT_DELTA = 2
MIN_STAT = 0
MAX_STAT = 100

# Applied when an action reports these events without naming their own size.
DEFAULT_DARKNESS_FEAR_INCREASE = 5
DEFAULT_FIRE_FEAR_REDUCTION = 5


def apply_effects(intent, player, game_map, skip_inventory: bool = False) -> None:
    """Apply an intent's fear, health, and inventory effects to the player.

    Fear and health deltas are clamped to +/-2 per turn and the resulting stats
    to 0..100, so a single interpreted intent cannot end a run on its own.

    ``skip_inventory`` is set by the caller when the action failed or was
    unknown, so AI-proposed inventory deltas cannot land on a fall-through.
    Fear and health deltas still apply unconditionally.
    """
    effects = getattr(intent, "effects", None) or {}

    fear_delta = max(-MAX_EFFECT_DELTA, min(MAX_EFFECT_DELTA, int(effects.get("fear", 0))))
    health_delta = max(-MAX_EFFECT_DELTA, min(MAX_EFFECT_DELTA, int(effects.get("health", 0))))

    player.fear = max(MIN_STAT, min(MAX_STAT, player.fear + fear_delta))
    player.health = max(MIN_STAT, min(MAX_STAT, player.health + health_delta))

    if skip_inventory:
        return

    for item_name in [str(x) for x in effects.get("inventory_remove", [])]:
        player.remove_item(item_name)

    # Adding is allowed only for a carryable item the game knows about and that
    # is actually present in the room, so the model cannot conjure inventory.
    room = game_map.current_room
    for item_name in [str(x) for x in effects.get("inventory_add", [])]:
        if item_name in game_map.items and room.has_item(item_name):
            item = room.remove_item(item_name)
            if item and item.is_carryable():
                player.add_item(item)


def handle_action_events(result, player, game_map, event_bus) -> None:
    """Convert an action result's event names into events on the bus.

    Two of them also move the player's stats directly: throwing into darkness
    costs fear, and a lit fire gives some back.
    """
    state_changes = result.state_changes or {}

    for event_name in result.events:
        if event_name == "player_moved":
            event_bus.emit(PlayerMovedEvent(
                from_room_id=state_changes.get("from_room_id", ""),
                to_room_id=state_changes.get("to_room_id", ""),
                direction=state_changes.get("direction", ""),
            ))

        elif event_name == "item_taken":
            event_bus.emit(ItemTakenEvent(
                item_name=state_changes.get("item_name", ""),
                room_id=game_map.current_room.id,
            ))

        elif event_name == "fuel_gathered":
            event_bus.emit(FuelGatheredEvent(
                item_name=state_changes.get("item_name", "firewood"),
            ))

        elif event_name == "item_dropped":
            event_bus.emit(ItemDroppedEvent(
                item_name=state_changes.get("item_name", ""),
                room_id=game_map.current_room.id,
            ))

        elif event_name == "item_thrown":
            event_bus.emit(ItemThrownEvent(
                item_name=state_changes.get("item_name", ""),
                target=state_changes.get("target"),
                into_darkness=False,
            ))

        elif event_name == "thrown_into_darkness":
            fear_increase = state_changes.get("fear_increase", DEFAULT_DARKNESS_FEAR_INCREASE)
            player.fear = min(MAX_STAT, player.fear + fear_increase)

        elif event_name == "power_restored":
            event_bus.emit(PowerRestoredEvent())

        elif event_name == "fire_lit":
            event_bus.emit(FireLitEvent())
            # Fire provides comfort, so it buys back some fear.
            fear_reduction = state_changes.get("fear_reduction", DEFAULT_FIRE_FEAR_REDUCTION)
            player.fear = max(MIN_STAT, player.fear - fear_reduction)

        elif event_name == "fire_no_fuel":
            event_bus.emit(FireAttemptEvent(has_fuel=False, has_matches=True))

        elif event_name == "use_light_switch_no_power":
            event_bus.emit(LightSwitchUsedEvent(has_power=False))

        elif event_name == "lights_on":
            event_bus.emit(LightSwitchUsedEvent(has_power=True))

        elif event_name == "use_fireplace_no_fuel":
            event_bus.emit(FireplaceUsedEvent(has_fuel=False))

        elif event_name == "use_fireplace":
            event_bus.emit(FireplaceUsedEvent(has_fuel=True))


def take_turn(
    text: str,
    *,
    player,
    game_map,
    quest_manager,
    action_registry,
    event_bus,
    set_feedback: Callable[[str], None],
) -> None:
    """Run one player command: interpret, execute, apply effects, emit events.

    The action runs before its effects are applied, so a failed or unknown
    action cannot let AI-proposed inventory changes land. Fear and health
    deltas still apply either way.

    ``set_feedback`` is called with the action's own narration before events
    are emitted, so a quest or cutscene listener can replace it with theirs.
    """
    context = build_ai_context(player, game_map, quest_manager)
    intent = interpret(text, context)

    result = action_registry.execute(intent.action, player, game_map, intent)

    if result is None:
        # No registered action. Fear and health still move; inventory does not.
        apply_effects(intent, player, game_map, skip_inventory=True)
        set_feedback(intent.reply or UNKNOWN_ACTION_FEEDBACK)
        return

    apply_effects(intent, player, game_map, skip_inventory=not result.success)
    set_feedback(result.feedback)
    handle_action_events(result, player, game_map, event_bus)
