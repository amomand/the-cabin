"""Move action for player movement between rooms."""

from __future__ import annotations

from game.actions.base import Action, ActionContext, ActionResult


class MoveAction(Action):
    """Handle player movement between rooms."""
    
    @property
    def name(self) -> str:
        return "move"
    
    def execute(self, ctx: ActionContext) -> ActionResult:
        direction = ctx.args.get("direction")
        
        if not direction:
            return ActionResult.failure_result(
                ctx.ai_reply or "You angle your body and stop. Where?"
            )
        
        # Store current room ID before moving
        from_room_id = ctx.room.id
        
        moved, message = ctx.map.move(direction, ctx.player)
        
        if moved:
            to_room_id = ctx.room.id
            return ActionResult.success_result(
                feedback="",  # No feedback during movement - room description speaks
                events=["player_moved", "entered_room"],
                state_changes={
                    "from_room_id": from_room_id,
                    "to_room_id": to_room_id,
                    "direction": direction
                }
            )
        else:
            # Movement failed - blocked or invalid direction
            return ActionResult.failure_result(
                ctx.ai_reply or message or "You test that way. The path isn't there."
            )
