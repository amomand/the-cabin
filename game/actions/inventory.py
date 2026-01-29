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
            return ActionResult.failure_result(ctx.ai_reply or "Take what?")
        
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
                feedback=ctx.ai_reply or f"You pick up the {item.name}. {item.name.title()} added to inventory.",
                events=events,
                state_changes=state_changes
            )
        elif item and not item.is_carryable():
            # Put the item back in the room
            room.add_item(item)
            return ActionResult.failure_result(
                ctx.ai_reply or f"That {item.name} can't be picked up."
            )
        else:
            # Item not found
            clean_name = room._clean_item_name(item_name)
            return ActionResult.failure_result(
                ctx.ai_reply or f"There's no {clean_name} here to pick up."
            )


class DropAction(Action):
    """Handle dropping items."""
    
    @property
    def name(self) -> str:
        return "drop"
    
    def execute(self, ctx: ActionContext) -> ActionResult:
        item_name = ctx.args.get("item")
        
        if not item_name:
            return ActionResult.failure_result(ctx.ai_reply or "Drop what?")
        
        item = ctx.player.remove_item(item_name)
        if not item:
            clean_name = ctx.player._clean_item_name(item_name)
            return ActionResult.failure_result(
                ctx.ai_reply or f"You don't have a {clean_name} to drop."
            )
        
        ctx.room.add_item(item)
        return ActionResult.success_result(
            feedback=ctx.ai_reply or f"You set the {item.name} down.",
            events=["item_dropped"],
            state_changes={"item_name": item.name}
        )
