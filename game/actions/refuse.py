"""Refuse action - Act V. Declining the coffee, in the estranged register.

The refusal is the climax of the rewritten canon (issue #141): at dawn the
copy offers the blue mug, and Elli says no in the voice of a woman speaking
to someone she does not know well. The copy cannot perform the estranged
register back at her, because nobody has ever seen the two of them in a room
after the twenty years. That gap is the way out.
"""

from __future__ import annotations

from game.actions.base import Action, ActionContext, ActionResult
from game.story import night_threshold_met


def _at_dawn_offer(ctx: ActionContext) -> bool:
    return (
        getattr(ctx.map.current_room, "id", None) == "cabin_main"
        and ctx.world_state.reunion_stage == "dawn"
    )


class RefuseAction(Action):
    """Refuse the offered comfort. Requires the knowing to have finished.

    Before recognition, the player doesn't yet know what there is to refuse,
    and the attempt lands as uncertainty. After recognition, refusal can only
    happen at the dawn offer, mug in the air between them.
    """

    @property
    def name(self) -> str:
        return "refuse"

    def execute(self, ctx: ActionContext) -> ActionResult:
        ws = ctx.world_state

        # Refusal requires both the accumulated night seams and the finished
        # knowing. Either alone is not enough: seams without recognition are
        # just unease, and recognition without seams should not be reachable
        # by normal play.
        if not ws.get("recognition", False) or not night_threshold_met(ws):
            return ActionResult.success_result(
                feedback=(
                    "The word sits in your mouth, shapeless. "
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

        if ws.ending == "escaped":
            return ActionResult.success_result(
                feedback=(
                    "It is already done. The room has stopped pretending. "
                    "What is left is the door, and south."
                ),
                events=["refuse_already_done"],
                state_changes={},
            )

        if not _at_dawn_offer(ctx):
            return ActionResult.success_result(
                feedback=(
                    "Not yet. The night has to finish. You keep your breath slow "
                    "and your eyes open and wait for the grey."
                ),
                events=["refuse_not_at_threshold"],
                state_changes={},
            )

        # The refusal itself. The register change, the estrangement spoken,
        # the grief spent back, the voicemail completed, the pretence
        # stopping. Elli stays in the wrong layer until she walks out.
        ws.ending = "escaped"
        return ActionResult.success_result(
            feedback=(
                "\"No,\" you say. \"Thank you.\"\n"
                "Not sharp. Nothing that could be argued with. Your voice comes out in "
                "the register you use across desks in glass rooms four thousand miles "
                "from here. Level. Courteous. Spaced. The register of a woman speaking "
                "to someone she does not know well.\n"
                "The mug stays in the air between you.\n\n"
                "\"You'll want something in you,\" it says. Nika's cadence, exact. "
                "\"It's a long walk on the compass.\"\n"
                "\"It was good of you to drive up,\" you say. \"With the roads like "
                "this. I know it's a long way to come for someone else's problem.\"\n"
                "Something moves behind the face. Not on it. Behind it. The warmth of "
                "the expression stays where it was put, and underneath, something "
                "adjusts, tries a purchase, finds none.\n\n"
                "\"Elli.\" Reproachful. Warm. A hand extended to the old shorthand. "
                "\"It's me.\"\n"
                "\"We haven't spoken properly in four years,\" you say, in the same "
                "level voice. \"I missed her mother's funeral. I sent flowers from an "
                "app. When she left me the message I listened to it eleven times and I "
                "wrote back about the camera.\" You keep your eyes on its eyes. That is "
                "the hardest part. The eyes are so exactly right. \"The last time I was "
                "in that shop she'd taped a photograph of me to the monitor by the "
                "till. Fourteen years old, that picture. She'd have taken it down if "
                "she'd known I'd seen it, so I never said. That is what we are now. She "
                "doesn't look at me the way you looked at me last night. Nobody has "
                "looked at me like that for twenty years. I made sure of it.\"\n\n"
                "The kettle goes on hissing on the stove, and then it does not, though "
                "no one has moved it.\n"
                "The thing wearing Nika sets the mug down on the table without a sound. "
                "When it speaks again the voice is still her voice, and the warmth is "
                "gone from under the words, as heat goes out of a stone.\n"
                "\"She counted the years,\" it says. \"Fourteen since you slept a night "
                "here. She has a number for it. She never once asked you to come home. "
                "Twenty years, and the message was the first time, and she sat at her "
                "kitchen table with the frost coming up the glass and made herself say "
                "it. And you wrote back about a camera.\"\n"
                "True things. All of them true, and hers, taken from her along with the "
                "towel and the lake path. Lies you could have walked away from.\n\n"
                "\"I know,\" you say. It comes out quieter than you mean, and you "
                "straighten your back and finish it, because there is one thing left in "
                "the account and it is hers too, and it belongs here.\n"
                "\"She told me one more thing. On the message. She said, it's lying out "
                "there.\"\n"
                "The room goes still. Even the fire.\n"
                "\"She warned me. I came anyway. I stayed the night. That part is "
                "mine.\" You take the breath your ribs allow. \"And you are still not "
                "her.\"\n\n"
                "The pretence stops.\n"
                "It does not fall away, or melt, or turn. It stops, mid-stance, between "
                "one breath and none, as an actor stops when the take is over. The face "
                "still made of Nika's face but no longer being worn from the inside. "
                "The fire goes to a grey that gives no light. The black of the ground "
                "outside comes up the walls to the window sills. The attention "
                "withdraws from your skin, all at once, everywhere. The sensation of a "
                "book being closed on a page.\n"
                "Nothing in the cabin is interested in you any more.\n\n"
                "You take your jacket off the peg. Your hands do the zip, the buttons "
                "at the collar, working on their own, well made, well trained. You put "
                "on your boots at the door. The door is behind you. South is real."
            ),
            events=["refuse", "ending_escaped"],
            state_changes={"ending": "escaped"},
        )
