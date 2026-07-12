"""Accept action - Act V. Drinking the offered coffee. The stayed ending.

Deliberately off-canon (the prose has no acceptance): the game keeps a
consent ending because a player can commit to the lie even though Elli
didn't. The horror is consent, not damnation. This ending closes the run.
"""

from __future__ import annotations

from game.actions.base import Action, ActionContext, ActionResult
from game.story import night_threshold_met


def _at_dawn_offer(ctx: ActionContext) -> bool:
    return (
        getattr(ctx.map.current_room, "id", None) == "cabin_main"
        and ctx.world_state.reunion_stage == "dawn"
    )


class AcceptAction(Action):
    """Accept the offered comfort. Requires the knowing to have finished."""

    @property
    def name(self) -> str:
        return "accept"

    def execute(self, ctx: ActionContext) -> ActionResult:
        ws = ctx.world_state

        if not ws.get("recognition", False) or not night_threshold_met(ws):
            return ActionResult.success_result(
                feedback=(
                    "The thought comes wrapped in warmth, too soft to hold. "
                    "You haven't yet understood what is being offered."
                ),
                events=["accept_too_early"],
                state_changes={},
            )

        if not ws.is_wrong_layer():
            return ActionResult.success_result(
                feedback="The offer is absent. Only the ordinary cabin cools in ordinary air.",
                events=["accept_no_target"],
                state_changes={},
            )

        if ws.ending == "escaped":
            return ActionResult.success_result(
                feedback=(
                    "The mug stands on the table where it was set down. The coffee has "
                    "stopped steaming. That door is closed now, and you closed it."
                ),
                events=["accept_after_refusal"],
                state_changes={},
            )

        if not _at_dawn_offer(ctx):
            return ActionResult.success_result(
                feedback=(
                    "The thought of staying finds no handle here. Not yet. The night "
                    "has its own order, and the offer comes with the grey."
                ),
                events=["accept_not_at_threshold"],
                state_changes={},
            )

        # The stayed ending. She knows, and drinks anyway.
        ws.ending = "stayed"
        return ActionResult.success_result(
            feedback=(
                "You take the mug.\n"
                "Your thumb finds the chip at the two o'clock of the handle, as it has "
                "gone there through every summer of your childhood, and you drink.\n"
                "The coffee is exactly right. It is always going to be exactly right.\n\n"
                "Nika smiles. The smile arrives on time now. Everything will arrive on "
                "time now. She turns to the stove and starts breakfast out of tins you "
                "never bought, talking as she always talked, in short runs with work in "
                "them, and the fire keeps the room ready for you, and your name sits "
                "warm in the walls.\n\n"
                "Outside the window the grey hangs where it hung. First light does not "
                "come. It does not need to. You are not walking out today, or the day "
                "after, and the compass on your jacket points at nothing from the peg "
                "by the door.\n\n"
                "It doesn't hurt. That was the flaw and now it is the mercy. Twenty "
                "years, and none of it is in the room. Nobody has looked at you like "
                "this for twenty years.\n"
                "You made sure of it. And here it is anyway, warm, patient, made "
                "without asking."
            ),
            events=["accept", "ending_stayed"],
            state_changes={"ending": "stayed"},
        )
