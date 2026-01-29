"""Use action for using items."""

from __future__ import annotations

from game.actions.base import Action, ActionContext, ActionResult


class UseAction(Action):
    """Handle using items."""
    
    @property
    def name(self) -> str:
        return "use"
    
    def execute(self, ctx: ActionContext) -> ActionResult:
        item_name = ctx.args.get("item")
        
        if not item_name:
            return ActionResult.failure_result(ctx.ai_reply or "Use what?")
        
        # Check if player has the item
        item = ctx.player.get_item(item_name)
        if not item:
            clean_name = ctx.player._clean_item_name(item_name)
            return ActionResult.failure_result(
                ctx.ai_reply or f"You don't have a {clean_name} to use."
            )
        
        item_lower = item.name.lower()
        
        # Circuit breaker - restores power
        if item_lower == "circuit breaker":
            ctx.world_state["has_power"] = True
            return ActionResult.success_result(
                feedback=ctx.ai_reply or "The circuit breaker clicks into place. Power hums through the cabin.",
                events=["power_restored", "item_used"],
                state_changes={"item_name": item.name, "has_power": True}
            )
        
        # Matches with firewood - lights fire
        if item_lower == "matches" and ctx.player.has_item("firewood"):
            ctx.world_state["fire_lit"] = True
            return ActionResult.success_result(
                feedback=ctx.ai_reply or "The matches catch and the firewood ignites. Warmth spreads through the cabin.",
                events=["fire_lit", "item_used"],
                state_changes={"item_name": item.name, "fire_lit": True}
            )
        
        # Matches without firewood
        if item_lower == "matches" and not ctx.player.has_item("firewood"):
            return ActionResult.success_result(
                feedback=ctx.ai_reply or "You strike a match, but you have nothing to light.",
                events=["fire_no_fuel"],
                state_changes={"item_name": item.name}
            )
        
        # Light switch - check power
        if item_lower == "light switch":
            if ctx.world_state.get("has_power", False):
                return ActionResult.success_result(
                    feedback=ctx.ai_reply or "The light switch clicks and the cabin fills with warm light.",
                    events=["lights_on"],
                    state_changes={"item_name": item.name}
                )
            else:
                return ActionResult.success_result(
                    feedback=ctx.ai_reply or "You flip the switch, but nothing happens. The cabin remains dark.",
                    events=["use_light_switch_no_power"],
                    state_changes={"item_name": item.name}
                )
        
        # Fireplace - check fuel
        if item_lower == "fireplace":
            if ctx.player.has_item("firewood"):
                return ActionResult.success_result(
                    feedback=ctx.ai_reply or "You could light a fire here if you had matches.",
                    events=["use_fireplace"],
                    state_changes={"item_name": item.name}
                )
            else:
                return ActionResult.success_result(
                    feedback=ctx.ai_reply or "The fireplace is cold and empty. You need fuel to start a fire.",
                    events=["use_fireplace_no_fuel"],
                    state_changes={"item_name": item.name}
                )
        
        # Generic use
        return ActionResult.success_result(
            feedback=ctx.ai_reply or f"You use the {item.name}.",
            events=["item_used"],
            state_changes={"item_name": item.name}
        )


class UseCircuitBreakerAction(Action):
    """Handle using the circuit breaker directly (room-based)."""
    
    @property
    def name(self) -> str:
        return "use_circuit_breaker"
    
    def execute(self, ctx: ActionContext) -> ActionResult:
        room = ctx.room
        
        if room.has_item("circuit breaker"):
            ctx.world_state["has_power"] = True
            return ActionResult.success_result(
                feedback=ctx.ai_reply or "With a satisfying thunk, the circuit breaker clicks into place. Power hums through the cabin.",
                events=["power_restored"],
                state_changes={"has_power": True}
            )
        
        return ActionResult.failure_result(
            ctx.ai_reply or "There's no circuit breaker here to use."
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
                ctx.ai_reply or "There's no light switch here."
            )
        
        if ctx.world_state.get("has_power", False):
            return ActionResult.success_result(
                feedback=ctx.ai_reply or "The lights flicker on, filling the cabin with warm illumination.",
                events=["lights_on"],
                state_changes={}
            )
        
        return ActionResult.success_result(
            feedback=ctx.ai_reply or "The light switch is unresponsive; the room remains shrouded in darkness.",
            events=["use_light_switch_no_power"],
            state_changes={}
        )
