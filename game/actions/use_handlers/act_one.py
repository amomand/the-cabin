"""Act I evidence, sauna, and sleep item-use handlers."""

from __future__ import annotations

from game.actions.base import ActionContext, ActionResult
from game.item import Item
from game.story import fear


def use_camera_feed(ctx: ActionContext, _item: Item) -> ActionResult:
    """Review the five-frame camera sequence."""
    if ctx.world_state.get("footage_reviewed", False):
        return ActionResult.authored(
            feedback=(
                "You open the older five frames again. The forked birch is still at the right edge, "
                "then left of centre. You look until your thumb aches."
            ),
        )
    ctx.world_state["footage_reviewed"] = True
    fear.shift(ctx.player, fear.CAMERA_FOOTAGE)
    return ActionResult.authored(
        feedback=(
            "Three feeds show frost and stillness. The northern one is dead. You open the saved sequence from five weeks ago.\n"
            "Five frames. In the first, a tall, narrow shape stands at the treeline and the forked birch is at the right edge. "
            "By the fourth, the shape is closer and the birch has moved left of centre. The ground beneath it is unmarked.\n"
            "Frame five is black."
        ),
    )


def use_sauna_stove(ctx: ActionContext, _item: Item) -> ActionResult:
    """Light the sauna stove and sit through the heat."""
    if ctx.world_state.get("sauna_used", False):
        return ActionResult.authored(
            feedback=(
                "The stones still hold their heat. Steam lifts from the ladle and is gone."
            ),
        )
    ctx.world_state["sauna_used"] = True
    return ActionResult.authored(
        feedback=(
            "You feed the stove until the stones begin to give back heat, then sit on the top bench in the dark. "
            "Water hisses on the stones and the sound fills the little room before it fades. "
            "For a while, the part of you that loves this place is not held at a distance."
        ),
    )


def use_bed(ctx: ActionContext, _item: Item) -> ActionResult:
    """Sleep only after the Act I evidence and sauna beats are complete."""
    if ctx.world_state.get("first_morning", False):
        return ActionResult.authored(
            feedback=(
                "You have slept enough. The morning waits outside."
            ),
        )
    if not ctx.world_state.get("fire_lit", False):
        return ActionResult.authored(
            feedback=(
                "The blankets are cold through. Without a fire they will not lose it."
            ),
        )
    unfinished = []
    if not ctx.world_state.get("voicemail_heard", False):
        unfinished.append("Nika's message waits on the phone.")
    if not ctx.world_state.get("footage_reviewed", False):
        unfinished.append("The saved frames are still unopened in the konttori.")
    if not ctx.world_state.get("sauna_used", False):
        unfinished.append("The sauna is still cold above the lake.")
    if unfinished:
        return ActionResult.authored(
            feedback=(
                "You sit on the edge of the bed. " + " ".join(unfinished) + " You get up."
            ),
        )
    ctx.world_state["first_morning"] = True
    return ActionResult.authored(
        feedback=(
            "You eat bread and packet soup at the square table, pour one glass of wine, and drink it. "
            "You cork the bottle on the counter, the empty glass beside it.\n"
            "Under the heavy covers, the isolation becomes total: the nearest lit window forty minutes south, "
            "no signal unless you hold the phone to the glass, the dark going on over the lake and bog.\n"
            "The fire ticks in the other room. You think of the empty hook and the scraping under the boards, "
            "then set yourself the morning's work: the northern camera in daylight, battery, moisture, board, in that order.\n"
            "You sleep better than you expect. You wake into silence. Then a log shifts in the hearth and puts sound back in the room. "
            "Ten past eight and the window is still black."
        ),
    )
