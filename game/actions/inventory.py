"""Inventory actions: take, drop, inventory."""

from __future__ import annotations

from game.actions.base import Action, ActionContext, ActionResult


class InventoryAction(Action):
    """Handle checking inventory."""
    
    @property
    def name(self) -> str:
        return "inventory"
    
    def execute(self, ctx: ActionContext) -> ActionResult:
        if ctx.ai_reply:
            return ActionResult.success_result(ctx.ai_reply)
        
        if ctx.player.inventory:
            items = ", ".join(item.name for item in ctx.player.inventory)
            return ActionResult.success_result(f"You check your bag: {items}.")
        
        return ActionResult.success_result("You check your bag. Just air and lint.")


class TakeAction(Action):
    """Handle picking up items."""
    
    @property
    def name(self) -> str:
        return "take"
    
    def execute(self, ctx: ActionContext) -> ActionResult:
        item_name = ctx.args.get("item")
        room = ctx.room
        
        if not item_name:
            return ActionResult.failure_result(ctx.ai_reply or "Your hand hovers, uncertain what to close around.")
        
        # Try to take the item from the room
        item = room.remove_item(item_name)
        
        if item and item.is_carryable():
            ctx.player.add_item(item)
            
            events = ["item_taken"]
            state_changes = {"item_name": item.name}
            
            # Special event for firewood
            if item.name.lower() == "firewood":
                events.append("fuel_gathered")
            
            return ActionResult.success_result(
                feedback=ctx.ai_reply or f"You pick up the {item.name} and stow it close.",
                events=events,
                state_changes=state_changes
            )
        elif item and not item.is_carryable():
            # Put the item back in the room
            room.add_item(item)
            return ActionResult.failure_result(
                ctx.ai_reply or f"The {item.name} stays fixed in the room, too heavy with place to come with you."
            )
        else:
            # Item not found
            clean_name = room._clean_item_name(item_name)
            return ActionResult.failure_result(
                ctx.ai_reply or f"You reach for the {clean_name}. Only cold air answers."
            )


class DropAction(Action):
    """Handle dropping items."""
    
    @property
    def name(self) -> str:
        return "drop"
    
    def execute(self, ctx: ActionContext) -> ActionResult:
        item_name = ctx.args.get("item")
        
        if not item_name:
            return ActionResult.failure_result(ctx.ai_reply or "Your hand opens around nothing.")
        
        item = ctx.player.remove_item(item_name)
        if not item:
            clean_name = ctx.player._clean_item_name(item_name)
            return ActionResult.failure_result(
                ctx.ai_reply or f"Your hand searches for the {clean_name}. It is not with you."
            )
        
        ctx.room.add_item(item)
        return ActionResult.success_result(
            feedback=ctx.ai_reply or f"You set the {item.name} down.",
            events=["item_dropped"],
            state_changes={"item_name": item.name}
        )
