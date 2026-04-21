"""Refuse action - Act V. Saying no to the Lyer."""

from __future__ import annotations

from game.actions.base import Action, ActionContext, ActionResult


class RefuseAction(Action):
    """Refuse the offered comfort. Requires recognition.

    Before recognition, the player doesn't yet know what there is to refuse,
    and the attempt lands as uncertainty. After recognition, refusal breaks
    the wrong layer and lands Elli back in the real clearing.
    """

    @property
    def name(self) -> str:
        return "refuse"

    def execute(self, ctx: ActionContext) -> ActionResult:
        ws = ctx.world_state

        # Refusal requires both that Elli has accumulated the wrongness (seen
        # enough tells to know something is off) and that she has reached
        # Recognition (the correction-turn). Either alone is not enough: tells
        # without recognition are just unease, and recognition without tells
        # should not be reachable by normal play.
        if not ws.get("recognition", False) or not ws.wrongness.threshold_met():
            return ActionResult.success_result(
                feedback=(
                    "Refuse what? The word sits in your mouth, shapeless. "
                    "You haven't yet let yourself say what there is to say no to."
                ),
                events=["refuse_too_early"],
                state_changes={},
            )

        if not ws.is_wrong_layer():
            return ActionResult.success_result(
                feedback="Nothing to refuse. Only the cabin, and the cold, and the drive home.",
                events=["refuse_no_target"],
                state_changes={},
            )

        # The refusal itself.
        ws.exit_wrong_layer()
        return ActionResult.success_result(
            feedback=(
                "\"No.\"\n"
                "You say it quietly. Not at her. At whatever is wearing her. "
                "At the cabin that was built around you. At the comfort that was prepared.\n"
                "\"No. I'm not staying.\"\n\n"
                "The world does not tear. It resolves. Like a lens settling. "
                "The fire is out. The mug is gone. The table is bare and dusty. "
                "The air smells of cold stone, not woodsmoke. "
                "Through the window, the real clearing: your own driveway, Nika's car, the real line of pines. "
                "Behind you, where she was sitting, nothing.\n\n"
                "You walk out. You do not look back. "
                "Somewhere far behind, in the trees that are not the trees you grew up with, "
                "something drags across wood. Slow. Patient. Already waiting for the next one."
            ),
            events=["refuse", "wrong_layer_exited", "ending_refused"],
            state_changes={"world_layer": "real"},
        )
