"""Accept action - Act V. Staying with the Lyer's offered comfort."""

from __future__ import annotations

from game.actions.base import Action, ActionContext, ActionResult


class AcceptAction(Action):
    """Accept the offered comfort. Requires recognition."""

    @property
    def name(self) -> str:
        return "accept"

    def execute(self, ctx: ActionContext) -> ActionResult:
        ws = ctx.world_state

        if not ws.get("recognition", False) or not ws.wrongness.threshold_met():
            return ActionResult.success_result(
                feedback=(
                    "Stay where? The thought comes wrapped in warmth, too soft to hold. "
                    "You haven't yet understood what is being offered."
                ),
                events=["accept_too_early"],
                state_changes={},
            )

        if not ws.is_wrong_layer():
            return ActionResult.success_result(
                feedback="There is no offer now. Only the ordinary cabin, cooling in ordinary air.",
                events=["accept_no_target"],
                state_changes={},
            )

        ws.exit_wrong_layer()
        ws.ending = "accepted"
        return ActionResult.success_result(
            feedback=(
                "You step back inside.\n"
                "Nika says your name once from the threshold. You do not answer right away. "
                "The fire is low and steady. The chair waits where it has always waited. "
                "The room is warm, and the warmth is not a disguise for anything sharper. "
                "That is the worst part. It is warm.\n\n"
                "You put your hand on the door and close it yourself.\n\n"
                "The latch settles. The cabin groans, not the door this time but the walls, "
                "the floor, the whole remembered shape of it. Outside, trees shudder without wind. "
                "Something releases.\n\n"
                "When you open the door again, morning has found the real clearing. The driveway. "
                "Nika's car. The familiar pines. The lake beyond them, ordinary and half frozen. "
                "The pull in your chest is gone.\n\n"
                "On the drive away, neither of you speaks. At the road, you notice the birches "
                "leaning slightly. Not toward the sun. Toward the cabin. You wonder if they have "
                "always done that."
            ),
            events=["accept", "wrong_layer_exited", "ending_accepted"],
            state_changes={"world_layer": "real", "ending": "accepted"},
        )
