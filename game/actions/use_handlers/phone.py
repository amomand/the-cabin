"""Phone use across the voicemail, false-cabin night, and escape coda."""

from __future__ import annotations

from game.actions.base import ActionContext, ActionResult
from game.item import Item
from game.story import AnomalyID, fear, observe_night_seam
from game.story.arrival import reopen_cabin
from game.actions.use_handlers.act_one import use_camera_feed


def use_phone(ctx: ActionContext, _item: Item) -> ActionResult:
    """Handle each story life of Elli's phone."""
    ws = ctx.world_state
    if ws.is_wrong_layer():
        if ws.ending == "escaped":
            return ActionResult.authored("You feel the phone through your jacket pocket. The compass is enough to watch.")
        if ws.reunion_stage in ("bedded", "night") and ws.ending == "none":
            text, _ = observe_night_seam(ws, AnomalyID.PHONE_DARK, ctx.player)
            return ActionResult.authored(
                feedback=text,
            )
        return ActionResult.authored(
            feedback=(
                "Your phone is in your jacket on the peg by the door. Your head "
                "is one enormous pulse. Later."
            ),
        )
    if ws.ending == "escaped":
        # The call belongs to the cabin window and its one bar. A carried
        # phone must not fire the beat from the wrong room.
        if getattr(ctx.map.current_room, "id", None) != "cabin_main":
            return ActionResult.authored(
                feedback=(
                    "No bar out here. The signal lives at the cabin "
                    "window, held to the glass, angled at the road."
                ),
            )
        if ws.coda_stage == "home":
            ws.transition_coda_to("called")
            fear.shift(ctx.player, fear.CODA_CALLED)
            return ActionResult.authored(
                feedback=(
                    "You go to the window and hold the phone to the glass until "
                    "the single bar surfaces, and ring Nika.\n"
                    "It rings four times. Long enough to see yourself in the dark "
                    "of the enamel sink, one cheekbone swollen, one eye going black.\n\n"
                    "\"Elli.\"\n"
                    "The pause holds all twenty years: your oldest friend not "
                    "knowing how to speak to you, boots half unlaced in a doorway, "
                    "both of you deciding how to stand. Your eyes go hot. The "
                    "damage is still in the line, real and yours.\n\n"
                    "\"You went up,\" she says.\n"
                    "\"Yes.\"\n"
                    "\"Alone.\" A breath goes out through the word. \"I told "
                    "you to wait.\"\n"
                    "\"I know.\"\n"
                    "The line hums with the distance, satellites and weather. "
                    "When she speaks again her voice has gone quieter, the "
                    "pricing-gun flatness with something under it that neither "
                    "of you is going to name today.\n"
                    "\"There's coffee at the shop. Come down before the light "
                    "goes. Drive slow past the lake.\"\n"
                    "\"I'm coming down,\" you say. \"Niks.\"\n"
                    "The pause this time is shorter. \"Drive slow,\" she says, and "
                    "rings off.\n\n"
                    "You stand at the window a moment longer. The clearing is "
                    "white under the first proper daylight, your tracks and the "
                    "fox's written across it. The treeline stands at the "
                    "distance it stands at today.\n"
                    "You start to pack."
                ),
            )
        if ws.coda_stage in ("called", "scraping"):
            return ActionResult.authored(
                feedback=(
                    "The call is made. The shop, the coffee, the road past the "
                    "lake. The phone has done what it can do."
                ),
            )
    if ctx.room.id != "cabin_main":
        return ActionResult.authored(
            "You feel the phone in your pocket. The message can wait until you are "
            "at the main-room window, where the signal reaches."
        )
    if ws.voicemail_heard:
        return use_camera_feed(ctx, _item)
    opening = reopen_cabin(ws)
    ws.voicemail_heard = True
    fear.shift(ctx.player, fear.VOICEMAIL_WARNING)
    return ActionResult.authored("\n\n".join(part for part in (
        opening,
        "You stand at the window and angle the phone towards the road. One bar. "
        "Nika's message is eleven days old. You put it to your ear.\n"
        "\"Elli. It's me. You need to come home. Something's wrong with the cabin. "
        "I don't know what. Don't go up on your own. Wait. It's... it's lying out there.\"\n"
        "The pause before the last line is the worst part. Nika does not pause. "
        "You had typed Call me tonight, whatever time, then deleted it. What you sent "
        "was a text about sorting the camera. She did not answer. "
        "The message ends. Beneath it, the saved pictures wait."
    ) if part))
