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
                        state_changes={"fire_lit": True, "fear_reduction": 5}
                    )
                else:
                    return ActionResult.failure_result(
                        "You kneel by the hearth. No matches. The firewood sits dark and cold."
                    )
            else:
                return ActionResult.failure_result(
                    "You hold a match to the empty hearth. It burns your fingers and goes out. You need firewood."
                )
        
        return ActionResult.failure_result(
            ctx.ai_reply or f"You can't light {target}."
        )
