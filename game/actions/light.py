"""Light action for lighting fires."""

from __future__ import annotations

from game.actions.base import Action, ActionContext, ActionResult
from game.actions.use_handlers.utilities import light_cabin_fire


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
                    return light_cabin_fire(ctx)
                else:
                    return ActionResult.authored(
                        "You kneel by the hearth. No matches. The firewood sits dark and cold.",
                        success=False,
                    )
            else:
                return ActionResult.authored(
                    "You hold a match to the empty hearth. No fuel catches. Heat bites your fingers and dies.",
                    success=False,
                )
        
        return ActionResult.failure_result(
            ctx.ai_reply or f"The {target} refuses the flame. The match gutters out."
        )
