"""Cabin utility fixture handlers."""

from __future__ import annotations

from game.actions.base import ActionContext, ActionResult
from game.events.requests import (
    FireplaceUsedRequest,
    FireAttemptRequest,
    FireLitRequest,
    LightSwitchUsedRequest,
    PowerRestoredRequest,
)
from game.item import Item
from game.story.arrival import reopen_cabin


def use_circuit_breaker(ctx: ActionContext, _item: Item) -> ActionResult:
    """Restore cabin power through the breaker fixture."""
    if ctx.world_state.has_power:
        return ActionResult.authored("The breaker is already up. The fridge hums through the wall.")
    ctx.world_state["has_power"] = True
    return ActionResult.authored(
        feedback="The breaker takes. Somewhere beyond the wall, the fridge shudders awake.",
        requests=[PowerRestoredRequest()],
    )


def light_cabin_fire(ctx: ActionContext) -> ActionResult:
    ws = ctx.world_state
    if ctx.room.id != "cabin_main" or ws.is_wrong_layer():
        return ActionResult.authored("You close the matchbox. The cabin hearth is the place for it.")
    if ws.ending != "none":
        return ActionResult.authored("You leave the hearth alone. The bag is still open beside the chair.")
    if ws.fire_lit:
        return ActionResult.authored("The fire is already burning. You leave the matches in their box.")
    if not ctx.player.has_item("firewood"):
        return ActionResult.authored(
            "You strike a match, but you have nothing to light.",
            requests=[FireAttemptRequest(has_fuel=False, has_matches=True)],
        )
    ws.fire_lit = True
    text = "The kindling catches. Heat begins at the hearth and nowhere else."
    if not ws.first_morning:
        opening = reopen_cabin(ws)
        if opening:
            text += "\n\n" + opening
    else:
        text += " You hold your stiff hands near it. The night is over; this warmth arrives too late for that."
    return ActionResult.authored(text, requests=[FireLitRequest(fear_reduction=5)])


def use_matches(ctx: ActionContext, _item: Item) -> ActionResult:
    return light_cabin_fire(ctx)


def use_light_switch(ctx: ActionContext, _item: Item) -> ActionResult:
    """Use the light switch without inventing power."""
    if ctx.world_state.get("has_power", False):
        return ActionResult.authored(
            feedback="The switch clicks. The ceiling bulb burns weak and yellow.",
            requests=[LightSwitchUsedRequest(has_power=True)],
        )
    return ActionResult.authored(
        feedback="The switch gives under your finger. Darkness stays where it is.",
        requests=[LightSwitchUsedRequest(has_power=False)],
    )


def use_fireplace(ctx: ActionContext, _item: Item) -> ActionResult:
    """Inspect whether the fireplace has fuel laid."""
    if ctx.world_state.is_wrong_layer():
        return ActionResult.authored(
            "The fire has gone to a grey that gives no light."
            if ctx.world_state.ending == "escaped" else
            "The logs glow along their centres. Someone has kept this fire."
        )
    if ctx.world_state.fire_lit:
        return ActionResult.authored("The hearth holds cold ash." if ctx.world_state.ending == "escaped" else "The logs burn low in the hearth.")
    if ctx.player.has_item("firewood"):
        return ActionResult.authored(
            feedback="The kindling is laid. You need the matches.",
            requests=[FireplaceUsedRequest(has_fuel=True)],
        )
    return ActionResult.authored(
        feedback="The grate is bare. Flame would have nothing to take.",
        requests=[FireplaceUsedRequest(has_fuel=False)],
    )
