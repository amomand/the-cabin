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
        
        # If AI provided a reply, use it
        if ctx.ai_reply:
            return ActionResult.success_result(ctx.ai_reply)
        
        # Build description from room, items, and wildlife
        base_description = room.get_description(ctx.player, ctx.world_state)
        items_description = room.get_items_description()
        
        # Add visible wildlife descriptions
        visible_wildlife = room.get_visible_wildlife()
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
        
        return ActionResult.success_result(full_description)


class ListenAction(Action):
    """Handle listening for sounds."""
    
    @property
    def name(self) -> str:
        return "listen"
    
    def execute(self, ctx: ActionContext) -> ActionResult:
        room = ctx.room
        
        # If AI provided a reply, use it
        if ctx.ai_reply:
            return ActionResult.success_result(ctx.ai_reply)
        
        # Describe wildlife sounds
        audible_wildlife = room.get_audible_wildlife()
        if audible_wildlife:
            sound_descriptions = [animal.sound_description for animal in audible_wildlife]
            return ActionResult.success_result(" ".join(sound_descriptions))
        
        return ActionResult.success_result(
            "You listen carefully, but hear only the wind through the trees."
        )
