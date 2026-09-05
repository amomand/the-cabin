"""Act I evidence, meals, sauna, and sleep."""
from __future__ import annotations

from game.actions.base import ActionContext, ActionResult
from game.item import Item
from game.story import fear
from game.story.arrival import COLD_NIGHT_HEALTH, evening_meal


def use_camera_feed(ctx: ActionContext, _item: Item) -> ActionResult:
    """The saved frames belong to the phone at the real cabin window."""
    ws = ctx.world_state
    if ws.is_wrong_layer():
        return ActionResult.authored("The screen stays dark. No pictures, no reflection.")
    if ws.first_morning and ws.ending == "none" and ctx.room.id == "cabin_grounds_main":
        if ws.camera_repaired:
            from game.story.morning import use_northern_camera
            return use_northern_camera(ctx, _item)
        return ActionResult.authored("You have the saved frames. The camera above you has no live picture yet.")
    if ctx.room.id != "cabin_main":
        return ActionResult.authored("You leave the pictures closed. At the cabin window, after the message.")
    if not ws.voicemail_heard:
        return ActionResult.authored("Nika's message waits above the saved pictures. You leave the pictures closed.")
    if ws.footage_reviewed:
        return ActionResult.authored(
            "You open the older five frames again. The forked birch is still at the right edge, "
            "then left of centre. You look until your thumb aches."
        )
    ws.footage_reviewed = True
    fear.shift(ctx.player, fear.CAMERA_FOOTAGE)
    return ActionResult.authored(
        "At the window you open the five frames saved on your phone. Five weeks old. "
        "You know them by heart. "
        "In the first, a tall, narrow shape stands at the treeline and the forked birch "
        "is at the right edge. By the fourth, the shape is closer and the birch has moved "
        "left of centre. The ground beneath it is unmarked. Frame five is black. "
        "Could be a deer, you told Nika. Not a deer, she said, and drove up. "
        "You close the pictures and put the phone in your pocket."
    )


def use_monitor(ctx: ActionContext, _item: Item) -> ActionResult:
    from game.story.real_rooms import konttori
    return ActionResult.authored(konttori(ctx.player, ctx.world_state, "The monitor stands on the desk."))


def use_table(ctx: ActionContext, _item: Item) -> ActionResult:
    ws = ctx.world_state
    if ws.is_wrong_layer():
        return ActionResult.authored("The table stands between you and the stove. The mug is on it.")
    if ws.first_morning or ws.ending != "none":
        return ActionResult.authored("The corked bottle stands on the counter, the empty glass beside it.")
    return ActionResult.authored(evening_meal(ws) or "The meal is finished. The bottle is corked.")


def use_sauna_stove(ctx: ActionContext, _item: Item) -> ActionResult:
    ws = ctx.world_state
    if ws.first_morning:
        return ActionResult.authored("The stones have gone cold. You keep your coat on. The camera comes first.")
    if ws.sauna_used:
        return ActionResult.authored("The stones still hold their heat. Steam lifts from the ladle and is gone.")
    ws.sauna_used = True
    light = "The low lights burn above the bench." if ws.has_power else "The firebox lights the edge of the bench."
    return ActionResult.authored(
        "You hang your towel by the door and feed the wood stove for half an hour. "
        "The stones begin to give back heat. " + light + " You sit on the top bench. "
        "Water hisses on the stones and fills the little room before it fades. "
        "Through the window the lake lies between the trunks. You held Nika's tenth "
        "birthday cake on your knees here because it was the only warm room in October. "
        "For a while, the part of you that loves this place is not held at a distance."
    )


def use_bed(ctx: ActionContext, _item: Item) -> ActionResult:
    ws = ctx.world_state
    if ws.first_morning:
        return ActionResult.authored("You have slept enough. The morning waits outside.")
    unfinished = []
    if not ws.voicemail_heard:
        unfinished.append("Nika's message waits on the phone, at the main-room window.")
    if not ws.footage_reviewed:
        unfinished.append("The saved pictures wait after it.")
    if unfinished:
        return ActionResult.authored("You sit on the edge of the bed. " + " ".join(unfinished) + " You get up.")
    meal = evening_meal(ws)
    ws.slept_cold = not ws.fire_lit
    ws.first_morning = True
    if ws.slept_cold:
        ctx.player.health = max(0, ctx.player.health - COLD_NIGHT_HEALTH)
        sleep = (
            "The blankets never quite lose their cold. You sleep in your clothes, "
            "waking whenever a knee slips out of the hollow your body has warmed. "
            "By morning your shoulders ache and your fingers are stiff.\n"
            "You wake into silence. The hearth gives nothing back. Your sleeve "
            "scrapes the sheet as you move, loud enough to make you stop."
        )
    else:
        sleep = (
            "The fire ticks in the other room. You sleep better than you expect. "
            "You wake into silence. Then a log shifts in the hearth and puts sound back in the room."
        )
    return ActionResult.authored("\n\n".join(part for part in (
        meal,
        "Under the heavy covers, the isolation becomes total: the nearest lit window "
        "forty minutes south, the dark going on over the lake and bog. You think of "
        "the empty hook and the scraping under the boards, then set yourself the "
        "morning's work: the northern camera in daylight, battery, moisture, board, in that order.",
        sleep + " Ten past eight and the window is still black."
    ) if part))
