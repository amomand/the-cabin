"""Refuse action - Act V. Declining the coffee, in the estranged register.

The refusal is the climax of the rewritten canon (issue #141): at dawn the
copy offers the blue mug, and Elli says no in the voice of a woman speaking
to someone she does not know well. The copy cannot perform the estranged
register back at her, because nobody has ever seen the two of them in a room
after the twenty years. That gap is the way out.
"""

from __future__ import annotations

from game.actions.base import Action, ActionContext, ActionResult
from game.ending import END_LINE_STAYED
from game.story import fear, night_threshold_met


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
                    "You almost say no. To what? You keep the word behind your teeth."
                ),
                events=["refuse_too_early"],
                state_changes={},
            )

        if not ws.is_wrong_layer():
            return ActionResult.success_result(
                feedback=(
                    "No mug waits between you and anyone. The cabin is cold. The road "
                    "home is where you left it."
                ),
                events=["refuse_no_target"],
                state_changes={},
            )

        if ws.ending != "none":
            if ws.ending in ("stayed", "accepted"):
                feedback = END_LINE_STAYED
            else:
                feedback = (
                    "It is already done. The room has stopped pretending. "
                    "What is left is the door, and south."
                )
            return ActionResult.success_result(
                feedback=feedback,
                events=[],
                state_changes={},
            )

        if not _at_dawn_offer(ctx):
            return ActionResult.success_result(
                feedback=(
                    "You keep quiet. Not while the face is turned away in the dark. "
                    "You will say it when it is looking at you."
                ),
                events=["refuse_not_at_threshold"],
                state_changes={},
            )

        # The refusal itself. The register change, the estrangement spoken,
        # the grief spent back, the voicemail completed, the pretence
        # stopping. Elli stays in the wrong layer until she walks out.
        if not ws.transition_ending_to("escaped"):
            return ActionResult.success_result(feedback=END_LINE_STAYED)
        fear.shift(ctx.player, fear.DAWN_ESCAPED)
        return ActionResult.success_result(
            feedback=(
                "\"No,\" you say. \"Thank you.\"\n"
                "You keep your voice level, courteous, spaced: the register you use "
                "across desks in glass rooms four thousand miles from here, a woman "
                "speaking to someone she does not know well.\n"
                "The mug stays in the air between you.\n\n"
                "\"You'll want something in you,\" it says in Nika's exact cadence. "
                "\"It's a long walk on the compass.\"\n"
                "\"It was good of you to drive up,\" you say. \"With the roads like "
                "this. I know it's a long way to come for someone else's problem.\"\n"
                "Something moves behind the face. The warmth of the expression stays "
                "where it was put while whatever is underneath adjusts, tries a "
                "purchase, and finds none.\n\n"
                "\"Elli.\" Warm reproach, a hand extended to the old shorthand. "
                "\"It's me.\"\n"
                "\"We haven't spoken properly in four years,\" you say, in the same "
                "level voice. \"I missed your mother's funeral. I sent flowers from an "
                "app. When you left me the message I listened to it eleven times and I "
                "wrote back about the camera.\" You keep your eyes on its eyes. That is "
                "the hardest part. The eyes are so exactly right. \"The last time I was "
                "in that shop you'd taped a photograph of me to the monitor by the "
                "till. Brown shoulder, sun in my hair. Fourteen years old. She'd have taken it down if "
                "you'd known I'd seen it, so I never said. That is what we are now. She "
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
                "Every word is true and belongs to Nika, grief taken from her along "
                "with the towel and the lake path. Lies you could have walked away from.\n\n"
                "\"I know,\" you say. It comes out quieter than you mean, and you "
                "straighten your back and finish it, because there is one thing left in "
                "the account and it is hers too, and it belongs here.\n"
                "\"She told me one more thing. On the message. She said, it's lying out "
                "there.\"\n"
                "The room goes still. Even the fire.\n"
                "\"She warned me. I came anyway. I stayed the night. That part is "
                "mine.\" You take the breath your ribs allow. \"And you are still not "
                "her.\"\n\n"
                "The pretence does not fall away. It simply stops mid-stance, between one breath "
                "and none, as an actor stops when the take is over. The face is still "
                "Nika's face, but nothing wears it from inside. The lamp burns. The fire "
                "has gone to a grey that gives no light. Black rises up the walls to the "
                "window sills, and the frost on the glass finishes in rings, the grain "
                "of a thing split open. The last warmth ends in a clean line before the "
                "hearth. Attention lifts from your skin like a book closing on a page.\n"
                "Nothing in the cabin is interested in you any more.\n\n"
                "You take your jacket off the peg. Your hands do the zip, the buttons "
                "at the collar, working on their own, well made, well trained. You put "
                "on your boots at the door and do not look at what stands by the stove "
                "in Nika's fleece. Whatever is under the face has never been shown to "
                "you. You keep it that way and put your hand on the latch."
            ),
            events=["refuse", "ending_escaped"],
            state_changes={"ending": "escaped"},
        )
