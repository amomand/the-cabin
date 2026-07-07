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

        # Build description from room, items, and wildlife
        base_description = room.get_description(ctx.player, ctx.world_state)
        items_description = room.get_items_description(ctx.world_state)
        
        # Add visible wildlife descriptions
        visible_wildlife = room.get_visible_wildlife(ctx.world_state)
        wildlife_description = ""
        if visible_wildlife:
            wildlife_descriptions = [animal.visual_description for animal in visible_wildlife]
            wildlife_description = " " + " ".join(wildlife_descriptions)
        
        # Combine all descriptions
        full_description = base_description
        if items_description:
            full_description += items_description
        if wildlife_description:
            full_description += wildlife_description
        if attention_prose:
            full_description += "\n\n" + attention_prose
        
        return ActionResult.success_result(full_description)


class ListenAction(Action):
    """Handle listening for sounds."""
    
    @property
    def name(self) -> str:
        return "listen"
    
    def execute(self, ctx: ActionContext) -> ActionResult:
        room = ctx.room
        attention_prose = ctx.map.observe_current_room("listen", ctx.player)

        # If AI provided a reply and there is no authored tell, use it.
        if ctx.ai_reply and not attention_prose:
            return ActionResult.success_result(ctx.ai_reply)
        if attention_prose:
            return ActionResult.success_result(attention_prose)
        
        # Describe wildlife sounds
        audible_wildlife = room.get_audible_wildlife(ctx.world_state)
        if audible_wildlife:
            sound_descriptions = [animal.sound_description for animal in audible_wildlife]
            return ActionResult.success_result(" ".join(sound_descriptions))
        
        return ActionResult.success_result(
            "You listen carefully, but hear only the wind through the trees."
        )
