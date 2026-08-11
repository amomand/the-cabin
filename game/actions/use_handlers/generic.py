"""Generic item-use fallback for non-story fixtures."""

from __future__ import annotations

from game.actions.base import ActionContext, ActionResult
from game.item import Item


def use_generic(ctx: ActionContext, item: Item) -> ActionResult:
    """Use model flavour when supplied, otherwise narrate the object locally."""
    item_lower = item.name.lower()
    if item_lower == "rope":
        feedback = "You pull the rope between both hands. The grey fibres hold."
    elif item_lower == "key":
        feedback = "You try the key against the nearest lock. It does not enter."
    else:
        feedback = f"You test the {item.name}. Nothing here changes."
    return ActionResult.success_result(
        feedback=ctx.ai_reply or feedback,
    )
