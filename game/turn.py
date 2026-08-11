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

from game.actions.base import ModelEffectsPolicy
from game.ai_context import build_ai_context
from game.ai_interpreter import interpret
from game.events.requests import (
    DarknessFearRequest,
    FireplaceUsedRequest,
    FireAttemptRequest,
    FireLitRequest,
    FuelGatheredRequest,
    ItemDroppedRequest,
    ItemTakenRequest,
    ItemThrownRequest,
    LightSwitchUsedRequest,
    PlayerMovedRequest,
    PowerRestoredRequest,
)
from game.events.types import (
    PlayerMovedEvent, ItemTakenEvent, ItemDroppedEvent, ItemThrownEvent,
    PowerRestoredEvent, FireLitEvent, FireAttemptEvent,
    LightSwitchUsedEvent, FireplaceUsedEvent, FuelGatheredEvent,
)


# Narrated fallback when the registry has no action for the interpreted intent
# and the model offered no reply of its own.
UNKNOWN_ACTION_FEEDBACK = (
    "You try it. Nothing here changes."
)

# Bounds on a single turn's AI-proposed deltas.
MAX_EFFECT_DELTA = 2
MIN_STAT = 0
MAX_STAT = 100


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
    """Dispatch an action result's typed requests in their declared order.

    Two of them also move the player's stats directly rather than going
    through a listener: throwing into darkness raises fear, and a lit fire
    lowers it.
    """
    for request in result.requests:
        if isinstance(request, PlayerMovedRequest):
            event_bus.emit(PlayerMovedEvent(
                from_room_id=request.from_room_id,
                to_room_id=request.to_room_id,
                direction=request.direction,
            ))

        elif isinstance(request, ItemTakenRequest):
            event_bus.emit(ItemTakenEvent(
                item_name=request.item_name,
                room_id=request.room_id,
            ))

        elif isinstance(request, FuelGatheredRequest):
            event_bus.emit(FuelGatheredEvent(
                item_name=request.item_name,
            ))

        elif isinstance(request, ItemDroppedRequest):
            event_bus.emit(ItemDroppedEvent(
                item_name=request.item_name,
                room_id=request.room_id,
            ))

        elif isinstance(request, ItemThrownRequest):
            event_bus.emit(ItemThrownEvent(
                item_name=request.item_name,
                target=request.target,
                into_darkness=request.into_darkness,
            ))

        elif isinstance(request, DarknessFearRequest):
            player.fear = max(
                MIN_STAT,
                min(MAX_STAT, player.fear + request.increase),
            )

        elif isinstance(request, PowerRestoredRequest):
            event_bus.emit(PowerRestoredEvent())

        elif isinstance(request, FireLitRequest):
            event_bus.emit(FireLitEvent())
            # Fire provides comfort, so it buys back some fear.
            player.fear = max(
                MIN_STAT,
                min(MAX_STAT, player.fear - request.fear_reduction),
            )

        elif isinstance(request, FireAttemptRequest):
            event_bus.emit(FireAttemptEvent(
                has_fuel=request.has_fuel,
                has_matches=request.has_matches,
            ))

        elif isinstance(request, LightSwitchUsedRequest):
            event_bus.emit(LightSwitchUsedEvent(has_power=request.has_power))

        elif isinstance(request, FireplaceUsedRequest):
            event_bus.emit(FireplaceUsedEvent(has_fuel=request.has_fuel))

        else:
            # ActionResult validates this boundary as well; keep the dispatcher
            # fail-closed if a malformed result is constructed by other means.
            raise TypeError(f"Unsupported turn request: {type(request).__name__}")


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

    The action runs before permitted model effects are applied, so a failed or
    unknown action cannot let AI-proposed inventory changes land. Fear and
    health deltas still apply either way. Authored results own their complete
    outcome and block model effects altogether.

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

    if result.model_effects is ModelEffectsPolicy.APPLY:
        apply_effects(intent, player, game_map, skip_inventory=not result.success)
    set_feedback(result.feedback)
    handle_action_events(result, player, game_map, event_bus)
