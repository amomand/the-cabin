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


def use_circuit_breaker(ctx: ActionContext, _item: Item) -> ActionResult:
    """Restore cabin power through the breaker fixture."""
    ctx.world_state["has_power"] = True
    return ActionResult.authored(
        feedback="The breaker takes. Somewhere beyond the wall, the fridge shudders awake.",
        requests=[PowerRestoredRequest()],
    )


def use_matches(ctx: ActionContext, _item: Item) -> ActionResult:
    """Try to light the fire with the carried matches."""
    if ctx.player.has_item("firewood"):
        ctx.world_state["fire_lit"] = True
        return ActionResult.authored(
            feedback="The kindling catches. Heat begins at the hearth and nowhere else.",
            requests=[FireLitRequest(fear_reduction=5)],
        )
    return ActionResult.authored(
        feedback="You strike a match, but you have nothing to light.",
        requests=[FireAttemptRequest(has_fuel=False, has_matches=True)],
    )


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
    if ctx.player.has_item("firewood"):
        return ActionResult.authored(
            feedback="The kindling is laid. You need the matches.",
            requests=[FireplaceUsedRequest(has_fuel=True)],
        )
    return ActionResult.authored(
        feedback="The grate is bare. Flame would have nothing to take.",
        requests=[FireplaceUsedRequest(has_fuel=False)],
    )
