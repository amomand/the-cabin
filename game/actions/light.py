"""Light action for lighting fires."""

from __future__ import annotations

from game.actions.base import Action, ActionContext, ActionResult


class LightAction(Action):
    """Handle lighting fires and fireplaces."""
    
    @property
    def name(self) -> str:
        return "light"
    
    def execute(self, ctx: ActionContext) -> ActionResult:
        target = ctx.args.get("target", "").lower()
        
        if "fire" in target or "fireplace" in target:
            if ctx.player.has_item("firewood"):
                if ctx.player.has_item("matches"):
                    ctx.world_state["fire_lit"] = True
                    return ActionResult.success_result(
                        feedback=ctx.ai_reply or "The matches catch and the firewood ignites. Warmth spreads through the cabin.",
                        events=["fire_lit", "fire_success"],
                        state_changes={"fire_lit": True}
                    )
                else:
                    return ActionResult.failure_result(
                        ctx.ai_reply or "You need matches to light the fire."
                    )
            else:
                return ActionResult.success_result(
                    feedback=ctx.ai_reply or "You can't light a fire without kindling or fuel.",
                    events=["use_fireplace_no_fuel"],
                    state_changes={}
                )
        
        return ActionResult.failure_result(
            ctx.ai_reply or f"You can't light {target}."
        )
