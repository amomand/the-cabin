"""Help action for showing available commands."""

from __future__ import annotations

from typing import List

from game.actions.base import Action, ActionContext, ActionResult


class HelpAction(Action):
    """Handle showing help/available commands."""
    
    @property
    def name(self) -> str:
        return "help"
    
    def execute(self, ctx: ActionContext) -> ActionResult:
        if ctx.ai_reply:
            return ActionResult.success_result(ctx.ai_reply)
        
        exits: List[str] = list(ctx.room.exits.keys())
        exits_str = ", ".join(exits) or "nowhere"
        
        return ActionResult.success_result(
            f"Keep it simple. Try 'go <direction>' — exits: {exits_str}. "
            "You can also 'look', 'listen', check 'inventory', 'take' items, 'use' items, or 'throw' things."
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
