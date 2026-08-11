"""Inventory actions: take, drop, inventory."""

from __future__ import annotations

from game.actions.base import Action, ActionContext, ActionResult
from game.events.requests import (
    FuelGatheredRequest,
    ItemDroppedRequest,
    ItemTakenRequest,
)


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
        
        return ActionResult.success_result("You check the bag. Empty.")


class TakeAction(Action):
    """Handle picking up items."""
    
    @property
    def name(self) -> str:
        return "take"
    
    def execute(self, ctx: ActionContext) -> ActionResult:
        item_name = ctx.args.get("item")
        room = ctx.room
        
        if not item_name:
            return ActionResult.failure_result(ctx.ai_reply or "Your hand moves, then stops. There is nothing there to take.")
        
        # Try to take the item from the room
        item = room.remove_item(item_name)
        
        if item and item.is_person():
            # Checked before carryability so no trait combination can ever put
            # a person in the bag. The fixed-in-place line below is written for
            # furniture; on a person it is ungrammatical and reduces her to an
            # object at the beat the act turns on.
            #
            # The authored lines win outright here; no `ctx.ai_reply or ...`.
            # The whole point of the branch is that no surface answers this with
            # object prose, and deferring to the model would hand that back to
            # the one thing the guard exists to catch.
            #
            # The layer and ending gates mirror `UseAction` exactly. Nika sits in
            # `cabin_main.items` in both layers, so without them `take nika` in
            # the real cabin would say she is standing there while `use nika`
            # says she isn't, and after the refusal it would call the thing in
            # her fleece "she", which the use path deliberately refuses to do.
            room.add_item(item)
            ws = ctx.world_state
            if not ws.is_wrong_layer():
                return ActionResult.authored("Nika isn't here.", success=False)
            if ws.ending == "escaped":
                return ActionResult.authored(
                    "You do not put a hand out towards the thing in Nika's fleece. "
                    "You have kept your eyes off it this long.",
                    success=False,
                )
            return ActionResult.authored(
                "You reach for her, then stop before your hand touches the sleeve.",
                success=False,
            )

        if item and item.is_carryable():
            ctx.player.add_item(item)
            
            requests = [ItemTakenRequest(item_name=item.name, room_id=room.id)]
            
            # Special event for firewood
            if item.name.lower() == "firewood":
                requests.append(FuelGatheredRequest(item_name=item.name))
            
            return ActionResult.success_result(
                feedback=ctx.ai_reply or f"You take the {item.name}.",
                requests=requests,
            )
        elif item and not item.is_carryable():
            # Put the item back in the room
            room.add_item(item)
            return ActionResult.failure_result(
                ctx.ai_reply or f"You test the {item.name}. It does not move."
            )
        else:
            # Item not found
            clean_name = room._clean_item_name(item_name)
            return ActionResult.failure_result(
                ctx.ai_reply or f"No {clean_name} is there."
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
            requests=[ItemDroppedRequest(
                item_name=item.name,
                room_id=ctx.room.id,
            )],
        )
