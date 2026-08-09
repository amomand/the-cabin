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
        
        exits = ctx.room.effective_exits(ctx.world_state)
        labels: List[str] = []
        seen_destinations = set()
        for alias, destination in exits.items():
            if destination in seen_destinations:
                continue
            seen_destinations.add(destination)

            label = alias
            try:
                location_id, room_id = destination
                room_name = ctx.map.locations[location_id].rooms[room_id].name
                if isinstance(room_name, str) and room_name:
                    label = room_name.removeprefix("The ").lower()
            except (AttributeError, KeyError, TypeError, ValueError):
                pass
            labels.append(f"the {label}")

        if labels:
            movement_hint = f"You mark the ways out: {', '.join(labels)}."
        else:
            movement_hint = "No path offers itself from here."
        
        return ActionResult.success_result(
            f"{movement_hint} The room, its sounds, what you carry, what your hands "
            "can reach. Start there."
        )


class NoneAction(Action):
    """Handle unknown/fallback actions with diegetic response."""
    
    @property
    def name(self) -> str:
        return "none"
    
    def execute(self, ctx: ActionContext) -> ActionResult:
        # If AI provided a reply, use it; otherwise use fallback
        feedback = ctx.ai_reply or "You try it. Nothing here changes."
        return ActionResult.success_result(feedback)
