"""Wait action - staying still, on purpose.

Waiting is how the night turns (the dawn beat) and how the story ends (the
coda: she sets the bag down, sits in her grandmother's chair, and listens).
Everywhere else it is a small authored beat of held time.
"""

from __future__ import annotations

from game.actions.base import Action, ActionContext, ActionResult
from game.story import can_advance_to_dawn, fear


class WaitAction(Action):
    """Handle waiting, sitting, staying still."""

    @property
    def name(self) -> str:
        return "wait"

    def execute(self, ctx: ActionContext) -> ActionResult:
        ws = ctx.world_state
        room_id = getattr(ctx.map.current_room, "id", None)

        # The false-cabin night. Waiting after the knowing brings the grey.
        if can_advance_to_dawn(ws, room_id):
            ws.transition_reunion_to("dawn")
            return ActionResult.authored(
                feedback=(
                    "You do not sleep. When you shift, the pain catches you under "
                    "the arm and you have to wait for it to loosen before you can "
                    "draw breath. You came through the door bleeding, barely able "
                    "to stand. You would have gone into any room with a fire. But "
                    "it was Nika you wanted at the table, Nika talking over dinner "
                    "as if there were nothing to get past. You let the evening "
                    "stay easy, even when the hand on your plate went wrong. "
                    "Later you let the door close. You heard your childhood handed "
                    "back across the dark and said night in return. You lie awake "
                    "now, wanting it still.\n\n"
                    "Grey comes into the window at last. The wrong grey, sourceless. "
                    "Below you, the breathing stops, without any of the business of "
                    "waking, and the thing that is not Nika gets up in one motion "
                    "and sets the kettle on. "
                    "It pours coffee into the blue mug and holds the mug out to you, "
                    "and its face makes Nika's morning face, the half-scowl before "
                    "the day's first words. "
                    "\"Drink up. We'll want the light.\""
                ),
            )

        if ws.is_wrong_layer() and room_id == "cabin_main" and ws.ending == "none":
            if ws.reunion_stage in ("bedded",):
                return ActionResult.authored(
                    feedback=(
                        "You lie still in the dark and wait for sleep that does not "
                        "come. You shift carefully under the covers."
                    ),
                )
            if ws.reunion_stage == "dawn":
                return ActionResult.authored(
                    feedback=(
                        "The arm holding the mug remains level. The coffee gives off "
                        "the same thin thread of steam."
                    ),
                )
            held_time = {
                "arrival": "You take a moment to catch your breath. Nika is waiting to hear what happened.",
                "tended": "You wait with Nika beside you. She has not finished checking you over.",
                "seated": "You sit a while with the coffee in front of you. You have not touched it yet.",
                "complete": "You sit a little longer in the warmth. Your ribs hurt less when you keep still.",
                "consented": "You have agreed to stay. You rest a moment before getting ready for bed.",
            }
            if ws.reunion_stage in held_time:
                return ActionResult.authored(held_time[ws.reunion_stage])

        if ws.is_wrong_layer() and ws.ending == "escaped":
            return ActionResult.authored(
                "You pause to catch your breath. Nothing moves towards you."
            )

        # The coda, back in the real cabin.
        if not ws.is_wrong_layer() and ws.ending == "escaped" and room_id == "cabin_main":
            if ws.coda_stage == "called":
                ws.transition_coda_to("scraping")
                fear.shift(ctx.player, fear.CODA_SCRAPING)
                return ActionResult.authored(
                    feedback=(
                        "You are packing when the scraping begins. "
                        "It comes from below, under the boards, or along them, slow and "
                        "rhythmic, something dragged with patience across a floor. The "
                        "same sound out of the same dark you lay rigid in at nine years "
                        "old, while your parents' voices explained it away through the "
                        "wall. Your hand tightens on the strap of the bag."
                    ),
                )
            if ws.coda_stage == "scraping":
                ws.transition_coda_to("end")
                return ActionResult.authored(
                    feedback=(
                        "The last time you ran from it, you ended up in the warm room. "
                        "You draw the zip closed and set the bag beside the door. "
                        "You pull out the chair, your "
                        "grandmother's chair, and sit at the table in your jacket with "
                        "your hands flat on the wood, facing the empty hook, and listen. "
                        "The scraping goes on for a while. "
                        "Then it stops."
                    ),
                )
            if ws.coda_stage == "home":
                return ActionResult.authored(
                    feedback=(
                        "You stand in the cold room a while. The hook stays empty. "
                        "The phone is in your pocket, and the window has its one bar."
                    ),
                )
            if ws.coda_stage == "end":
                return ActionResult.authored("You stay in the chair. The scraping has stopped.")

        if ws.first_morning and not ws.is_wrong_layer() and ws.ending == "none" and room_id == "old_woods":
            return ActionResult.authored("You stand in your own boot marks. The cold works through your soles. Go back.")

        if (not ws.is_wrong_layer() and ws.ending == "escaped"
                and ws.coda_stage == "scraping" and room_id in ("konttori", "bedroom")):
            return ActionResult.authored("You wait by the doorway, listening to the scraping.")

        # Held time, anywhere else.
        return ActionResult.authored(
            "You wait a while. The quiet holds." if ws.first_morning
            else "You give yourself a moment before going on."
        )
