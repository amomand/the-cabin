"""Throw action for throwing items at targets."""

from __future__ import annotations

from game.actions.base import Action, ActionContext, ActionResult


class ThrowAction(Action):
    """Handle throwing items."""
    
    @property
    def name(self) -> str:
        return "throw"
    
    def execute(self, ctx: ActionContext) -> ActionResult:
        item_name = ctx.args.get("item")
        target_name = ctx.args.get("target")
        room = ctx.room
        
        if not item_name:
            return ActionResult.failure_result(ctx.ai_reply or "Throw what?")
        
        # Check if player has the item
        item = ctx.player.get_item(item_name)
        if not item:
            clean_name = ctx.player._clean_item_name(item_name)
            return ActionResult.failure_result(
                ctx.ai_reply or f"You don't have a {clean_name} to throw."
            )
        
        if not item.is_throwable():
            return ActionResult.failure_result(
                ctx.ai_reply or f"The {item.name} isn't something you can throw."
            )
        
        # Remove item from inventory
        ctx.player.remove_item(item_name)
        
        events = ["item_thrown"]
        state_changes = {"item_name": item.name}
        
        # If throwing at a specific target (wildlife)
        if target_name and room.has_wildlife(target_name):
            animal = room.get_wildlife(target_name)
            if animal:
                result = animal.provoke()
                events.append("wildlife_provoked")
                state_changes["target"] = target_name
                state_changes["provoke_result"] = result["action"]
                
                if result["action"] == "attack":
                    # Animal attacks - apply damage
                    return ActionResult.success_result(
                        feedback=result["message"],
                        events=events + ["wildlife_attack"],
                        state_changes={
                            **state_changes,
                            "health_damage": result["health_damage"],
                            "fear_increase": result["fear_increase"]
                        }
                    )
                elif result["action"] in ["flee", "wander"]:
                    # Animal leaves
                    if result.get("remove_from_room"):
                        room.remove_wildlife(target_name)
                    return ActionResult.success_result(
                        feedback=result["message"],
                        events=events + ["wildlife_fled"],
                        state_changes=state_changes
                    )
                else:
                    # Animal ignores
                    return ActionResult.success_result(
                        feedback=result["message"],
                        events=events,
                        state_changes=state_changes
                    )
            else:
                return ActionResult.success_result(
                    feedback=f"You throw the {item.name} at the {target_name}, but miss.",
                    events=events,
                    state_changes=state_changes
                )
        
        # Throwing into darkness (no specific target)
        feedback = ctx.ai_reply or f"The {item.name} flies into the dark. You hear a dull thunk in the distance... and something else."
        return ActionResult.success_result(
            feedback=feedback,
            events=events + ["thrown_into_darkness"],
            state_changes={**state_changes, "fear_increase": 5}
        )
