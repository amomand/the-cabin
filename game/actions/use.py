"""Registry-facing use actions."""

from __future__ import annotations

from game.actions.base import Action, ActionContext, ActionResult
from game.actions.use_handlers import ITEM_USE_HANDLERS, use_generic
from game.actions.use_handlers.utilities import use_circuit_breaker, use_light_switch


class UseAction(Action):
    """Resolve an item, then delegate its cohesive behavior to a handler."""

    @property
    def name(self) -> str:
        return "use"

    def execute(self, ctx: ActionContext) -> ActionResult:
        item_name = ctx.args.get("item")

        if not item_name:
            return ActionResult.failure_result(
                ctx.ai_reply or "Your hand searches for something to use and finds only air."
            )

        # Check inventory first, then the current room for non-carryable
        # fixtures. This resolution order remains the public UseAction seam.
        # The phone is carried story equipment, not a movable room item.
        clean = ctx.player._clean_item_name(item_name)
        if clean in ("phone", "camera feed", "frames", "pictures"):
            name = "phone" if clean == "phone" else "camera feed"
            return ITEM_USE_HANDLERS[name](ctx, ctx.map.items[name])
        item = ctx.player.get_item(item_name)
        if not item:
            item = ctx.room.get_item(item_name)
        if not item:
            clean_name = ctx.player._clean_item_name(item_name)
            return ActionResult.failure_result(
                ctx.ai_reply or f"You reach for the {clean_name}, but your hand closes on empty air."
            )

        handler = ITEM_USE_HANDLERS.get(item.name.lower(), use_generic)
        return handler(ctx, item)


class UseCircuitBreakerAction(Action):
    """Handle using the circuit breaker directly (room-based)."""

    @property
    def name(self) -> str:
        return "use_circuit_breaker"

    def execute(self, ctx: ActionContext) -> ActionResult:
        room = ctx.room

        if room.has_item("circuit breaker"):
            return use_circuit_breaker(ctx, room.get_item("circuit breaker"))

        return ActionResult.failure_result(
            "Your hand finds only wall and cold paint."
        )


class TurnOnLightsAction(Action):
    """Handle turning on lights."""

    @property
    def name(self) -> str:
        return "turn_on_lights"

    def execute(self, ctx: ActionContext) -> ActionResult:
        room = ctx.room

        if not room.has_item("light switch"):
            return ActionResult.failure_result(
                ctx.ai_reply or "Your hand searches the wall and finds no switch."
            )

        return use_light_switch(ctx, room.get_item("light switch"))
