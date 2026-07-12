"""Wait action - staying still, on purpose.

Waiting is how the night turns (the dawn beat) and how the story ends (the
coda: she sets the bag down, sits in her grandmother's chair, and listens).
Everywhere else it is a small authored beat of held time.
"""

from __future__ import annotations

from game.actions.base import Action, ActionContext, ActionResult
from game.story import night_threshold_met


class WaitAction(Action):
    """Handle waiting, sitting, staying still."""

    @property
    def name(self) -> str:
        return "wait"

    def execute(self, ctx: ActionContext) -> ActionResult:
        ws = ctx.world_state
        room_id = getattr(ctx.map.current_room, "id", None)

        # The false-cabin night. Waiting after the knowing brings the grey.
        # The dawn gate matches refuse/accept and _act_v_offer_active:
        # recognition AND the gathered seams, so a malformed save cannot
        # reach an offer it would then be unable to answer.
        if ws.is_wrong_layer() and room_id == "cabin_main" and ws.ending == "none":
            if (
                ws.reunion_stage == "night"
                and ws.get("recognition", False)
                and night_threshold_met(ws)
            ):
                ws.reunion_stage = "dawn"
                return ActionResult.success_result(
                    feedback=(
                        "You do not sleep, and you do not pretend to think about what "
                        "to do, because there is no list of options to work through and "
                        "for once in your life you do not reach for one. You lie in the "
                        "warmth it keeps for you and wait.\n\n"
                        "Grey comes into the window at last. The wrong grey, sourceless. "
                        "Below you, the breathing stops, without any of the business of "
                        "waking, and the thing that is not Nika gets up in one motion "
                        "and sets the kettle on.\n"
                        "It pours coffee into the blue mug and holds the mug out to you, "
                        "and its face makes Nika's morning face, the half-scowl before "
                        "the day's first words.\n"
                        "\"Drink up. We'll want the light.\""
                    ),
                    events=["wait", "dawn"],
                    state_changes={"reunion_stage": "dawn"},
                )
            if ws.reunion_stage in ("bedded",):
                return ActionResult.success_result(
                    feedback=(
                        "You lie still in the dark and wait for sleep that does not "
                        "come. The night is long, and it is not done showing you things."
                    ),
                    events=["wait_night"],
                    state_changes={},
                )
            if ws.reunion_stage == "dawn":
                return ActionResult.success_result(
                    feedback=(
                        "The mug stays in the air between you. It does not tire. "
                        "It has never been tired."
                    ),
                    events=["wait_dawn"],
                    state_changes={},
                )

        # The coda, back in the real cabin.
        if not ws.is_wrong_layer() and ws.ending == "escaped" and room_id == "cabin_main":
            if ws.coda_stage == "called":
                ws.coda_stage = "scraping"
                return ActionResult.success_result(
                    feedback=(
                        "You are packing when the scraping begins.\n"
                        "It comes from below, under the boards, or along them, slow and "
                        "rhythmic, something dragged with patience across a floor. The "
                        "same sound out of the same dark you lay rigid in at nine years "
                        "old, while your parents' voices explained it away through the "
                        "wall.\n"
                        "You are not nine now. You know what you have been listening to "
                        "all your life. Not something trying to get in. Something "
                        "letting you know it is there."
                    ),
                    events=["wait", "coda_scraping"],
                    state_changes={"coda_stage": "scraping"},
                )
            if ws.coda_stage == "scraping":
                ws.coda_stage = "end"
                return ActionResult.success_result(
                    feedback=(
                        "It moved you once, and you ran, and the running took you "
                        "exactly where it wanted you.\n"
                        "You set the bag down. You pull out the chair, your "
                        "grandmother's chair, and sit at the table in your jacket with "
                        "your hands flat on the wood, facing the empty hook, and listen.\n\n"
                        "The scraping goes on for a while.\n"
                        "Then it stops."
                    ),
                    events=["wait", "coda_end", "ending_complete"],
                    state_changes={"coda_stage": "end"},
                )
            if ws.coda_stage == "home":
                return ActionResult.success_result(
                    feedback=(
                        "You stand in the cold room a while. The hook stays empty. "
                        "The phone is in your pocket, and the window has its one bar."
                    ),
                    events=["wait_coda"],
                    state_changes={},
                )

        # Held time, anywhere else.
        return ActionResult.success_result(
            feedback=ctx.ai_reply or (
                "You stand still and let the quiet have its minute. "
                "Nothing in it asks you to hurry."
            ),
            events=["wait"],
            state_changes={},
        )
