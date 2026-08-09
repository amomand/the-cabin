"""Throw action for throwing items at targets."""

from __future__ import annotations

from game.actions.base import Action, ActionContext, ActionResult


INDOOR_THROW_FEEDBACK = {
    "cabin_main": (
        "The {item_name} leaves your hand, strikes the floorboards, "
        "and rattles toward the hearth."
    ),
    "konttori": (
        "The {item_name} clips the office wall and drops among the scattered papers."
    ),
    "bedroom": (
        "The {item_name} hits the bedroom floor with a hard, small sound."
    ),
    "sauna": (
        "The {item_name} cracks against the sauna bench and drops to the boards."
    ),
}

DEFAULT_INDOOR_THROW_FEEDBACK = (
    "The {item_name} leaves your hand, strikes the room hard, "
    "and drops close by."
)


class ThrowAction(Action):
    """Handle throwing items."""
    
    @property
    def name(self) -> str:
        return "throw"
    
    def execute(self, ctx: ActionContext) -> ActionResult:
        item_name = ctx.args.get("item")
        room = ctx.room
        
        if not item_name:
            return ActionResult.failure_result(ctx.ai_reply or "Your hand tightens around nothing.")
        
        # Check if player has the item
        item = ctx.player.get_item(item_name)
        if not item:
            clean_name = ctx.player._clean_item_name(item_name)
            return ActionResult.failure_result(
                ctx.ai_reply or f"You reach for the {clean_name}. It is not with you."
            )
        
        if not item.is_throwable():
            return ActionResult.failure_result(
                ctx.ai_reply or f"The {item.name} sits wrong in your grip. It will not leave your hand like that."
            )
        
        # Remove item from inventory
        ctx.player.remove_item(item_name)
        
        events = ["item_thrown"]
        state_changes = {"item_name": item.name}

        # Untargeted throws are authored here so spatial truth follows the room.
        room_id = getattr(room, "id", "")
        if getattr(room, "is_indoors", False):
            room.add_item(item)
            feedback_template = INDOOR_THROW_FEEDBACK.get(room_id, DEFAULT_INDOOR_THROW_FEEDBACK)
            feedback = feedback_template.format(item_name=item.name)
            return ActionResult.success_result(
                feedback=feedback,
                events=events,
                state_changes=state_changes
            )

        # Throwing into darkness outdoors (no specific target)
        feedback = ctx.ai_reply or (
            f"The {item.name} strikes somewhere past the bend. "
            "A second knock answers from farther in."
        )
        return ActionResult.success_result(
            feedback=feedback,
            events=events + ["thrown_into_darkness"],
            state_changes={**state_changes, "fear_increase": 5}
        )
