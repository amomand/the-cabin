"""Accept action - Act V. Drinking the offered coffee. The stayed ending.

Deliberately off-canon (the prose has no acceptance): the game keeps a
consent ending because a player can commit to the lie even though Elli
didn't. The horror is consent, not damnation. This ending closes the run.
"""

from __future__ import annotations

from game.actions.base import Action, ActionContext, ActionResult
from game.story import fear, night_threshold_met


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
            return ActionResult.authored(
                feedback=(
                    "The blue mug is not in your hands. Whatever you mean by yes, no "
                    "one has asked yet."
                ),
            )

        if not ws.is_wrong_layer():
            return ActionResult.authored(
                feedback=(
                    "No one is holding out the blue mug. The real cabin is cold around you."
                ),
            )

        if ws.ending == "escaped":
            return ActionResult.authored(
                feedback=(
                    "The mug stands on the table where it was set down. The coffee has "
                    "stopped steaming. That door is closed now, and you closed it."
                ),
            )

        if not _at_dawn_offer(ctx):
            return ActionResult.authored(
                feedback=(
                    "The blue mug is rinsed by the sink. No one is holding it out to "
                    "you. The offer has not been made."
                ),
            )

        # The stayed ending. She knows, and drinks anyway.
        ws.ending = "stayed"
        fear.shift(ctx.player, fear.DAWN_STAYED)
        return ActionResult.authored(
            feedback=(
                "You take the mug.\n"
                "Your thumb finds the chip at the two o'clock of the handle, as it has "
                "gone there through every summer of your childhood, and you drink.\n"
                "The coffee is pale with milk, no sugar, and tastes of being twelve "
                "with lake water in your hair. You know what it is and drink again.\n\n"
                "Nika turns to the stove and starts breakfast from the tins. She talks "
                "about Jukka's knee and Thursday's delivery, in short runs with work in "
                "them. When she smiles, her mouth and her eyes move together. You notice "
                "because you were waiting for the fault. Then you stop checking.\n\n"
                "Outside the window, the grey does not lift. Frost covers the glass in "
                "finished rings. Your jacket stays on its peg, the compass clipped to it.\n\n"
                "Nothing hurts, and you know why. The answer changes nothing.\n"
                "\"More?\" Nika asks.\n"
                "You hold out the mug."
            ),
        )
