"""Refuse action - Act V. Saying no to the Lyer."""

from __future__ import annotations

from game.actions.base import Action, ActionContext, ActionResult


def _at_offer_threshold(ctx: ActionContext) -> bool:
    return getattr(ctx.map.current_room, "id", None) == "cabin_clearing"


class RefuseAction(Action):
    """Refuse the offered comfort. Requires recognition.

    Before recognition, the player doesn't yet know what there is to refuse,
    and the attempt lands as uncertainty. After recognition, refusal can only
    happen at the wrong cabin threshold, where the offered warmth is present.
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

        if not _at_offer_threshold(ctx):
            return ActionResult.success_result(
                feedback=(
                    "You try to make the word mean something, but the cabin is not in front of you. "
                    "There is only dark wood, cold air, and the pull north."
                ),
                events=["refuse_not_at_threshold"],
                state_changes={},
            )

        # The refusal itself.
        ws.exit_wrong_layer()
        ws.ending = "refused"
        return ActionResult.success_result(
            feedback=(
                "\"No.\"\n"
                "You say it quietly. Not at her. At whatever is wearing her. "
                "At the cabin that was built around you. At the comfort that was prepared.\n"
                "\"No. I'm not staying.\"\n\n"
                "You turn from the door. Nika turns with you.\n\n"
                "You walk. South, or what your bodies agree to call south. The forest folds "
                "the path back on itself. The cabin waits in the next clearing, and the next, "
                "each time with the fire burning low and the chairs facing the hearth. Each "
                "time the warmth reaches. Each time you say no.\n\n"
                "Time breaks into pieces too small to count. The animals stand closer. The "
                "silence grows heavy enough to lean against. Still you walk.\n\n"
                "At last the ground hardens under your boots. Gravel shows through the frost. "
                "The driveway opens ahead, Nika's car rimed white in the morning light. The cabin "
                "stays behind you. The pull in your chest does not leave. It only thins, a faint "
                "lean north, toward a door that is always open."
            ),
            events=["refuse", "wrong_layer_exited", "ending_refused"],
            state_changes={"world_layer": "real", "ending": "refused"},
        )
