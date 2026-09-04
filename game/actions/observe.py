"""Observation actions: look and listen."""

from __future__ import annotations

from game.actions.base import Action, ActionContext, ActionResult


class LookAction(Action):
    """Handle looking around the room."""
    
    @property
    def name(self) -> str:
        return "look"
    
    def execute(self, ctx: ActionContext) -> ActionResult:
        room = ctx.room
        attention_prose = ctx.map.observe_current_room("look", ctx.player)

        # If AI provided a reply and there is no authored tell, use it.
        if ctx.ai_reply and not attention_prose:
            return ActionResult.success_result(ctx.ai_reply)

        # Build description from room and items. A look from inside the room
        # is always a revisit: arriving has already shown the room once, so a
        # description must not narrate the arrival again.
        base_description = room.get_description(
            ctx.player, ctx.world_state, revisit=True
        )
        items_description = room.get_items_description(ctx.world_state)

        # Combine all descriptions
        full_description = base_description
        if items_description:
            full_description += items_description
        if attention_prose:
            full_description += "\n\n" + attention_prose
            return ActionResult.authored(full_description)
        return ActionResult.success_result(full_description)


class ListenAction(Action):
    """Handle listening for sounds."""
    
    @property
    def name(self) -> str:
        return "listen"
    
    def execute(self, ctx: ActionContext) -> ActionResult:
        attention_prose = ctx.map.observe_current_room("listen", ctx.player)

        # If AI provided a reply and there is no authored tell, use it.
        if ctx.ai_reply and not attention_prose:
            return ActionResult.success_result(ctx.ai_reply)
        if attention_prose:
            return ActionResult.authored(attention_prose)

        if getattr(ctx.room, "is_indoors", False):
            return ActionResult.success_result(
                "You hold still. A board ticks once, then settles. Nothing else."
            )

        if ctx.world_state.first_morning and not ctx.world_state.is_wrong_layer():
            return ActionResult.authored("No wind. No birds. You hear your coat move when you breathe.")
        return ActionResult.success_result(
            "Wind moves high in the trees. Near the ground, nothing answers."
        )
