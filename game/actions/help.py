"""Help action for giving an in-world nudge."""

from __future__ import annotations

from typing import List

from game.actions.base import Action, ActionContext, ActionResult


class HelpAction(Action):
    """Handle help without exposing command syntax to the player."""
    
    @property
    def name(self) -> str:
        return "help"
    
    def execute(self, ctx: ActionContext) -> ActionResult:
        if ctx.ai_reply:
            return ActionResult.success_result(ctx.ai_reply)
        
        exits: List[str] = list(ctx.room.effective_exits(ctx.world_state).keys())
        if exits:
            exits_str = ", ".join(exits)
            movement_hint = f"The possible ways out press at you: {exits_str}."
        else:
            movement_hint = "There is no obvious way out from here."
        
        return ActionResult.success_result(
            f"{movement_hint} Let your attention settle on the room, the sounds, "
            "what you carry, what lies within reach, and what your hands can do."
        )


class NoneAction(Action):
    """Handle unknown/fallback actions with diegetic response."""
    
    @property
    def name(self) -> str:
        return "none"
    
    def execute(self, ctx: ActionContext) -> ActionResult:
        # If AI provided a reply, use it; otherwise use fallback
        feedback = ctx.ai_reply or "You start, then think better of it. The cold in your chest makes you careful."
        return ActionResult.success_result(feedback)
