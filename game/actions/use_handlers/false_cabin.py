"""False-cabin reunion, night, and dawn item-use handlers."""

from __future__ import annotations

from game.actions.base import ActionContext, ActionResult
from game.item import Item
from game.story import (
    AnomalyID,
    fear,
    log_tell,
    maybe_finish_the_knowing,
    observe_night_seam,
)
from game.story.evening import observe_evening_through


def _observe_tell(
    *,
    anomaly: AnomalyID,
    world_state,
    player,
) -> ActionResult:
    """Log Act III evening beats through this tell and narrate them.

    Tells land in story order even if the fixtures are inspected out of
    order. Re-using a fixture returns its callback without double-logging.
    """
    narration = observe_evening_through(world_state, anomaly, player)
    return ActionResult.authored(
        feedback=narration,
    )


def use_window(ctx: ActionContext, _item: Item) -> ActionResult:
    """Observe the window's layer- and reunion-aware tell."""
    if not ctx.world_state.is_wrong_layer():
        return ActionResult.success_result(
            feedback="You glance out the window. The clearing. The treeline. Home.",
        )
    stage = ctx.world_state.reunion_stage
    if stage in ("arrival", "tended", "seated"):
        return ActionResult.authored(
            feedback=(
                "You glance at the window. The light outside is flat and white, "
                "with no sun in it. You don't look for long. Not yet."
            ),
        )
    if stage != "complete":
        return ActionResult.authored(
            feedback=(
                "Beyond the glass: black ground, close trees, no sky you can use. "
                "You stay on the warm side of it."
            ),
        )
    return _observe_tell(
        player=ctx.player,
        anomaly=AnomalyID.FROST_WOOD_GRAIN,
        world_state=ctx.world_state,
    )


def use_mug(ctx: ActionContext, _item: Item) -> ActionResult:
    """Handle the real mug, reunion coffee, night seam, and dawn consent."""
    ws = ctx.world_state
    if not ws.is_wrong_layer():
        if not ws.get("fire_lit", False) or not ws.get("has_power", False):
            return ActionResult.success_result(
                feedback="The hook is empty. The cupboard can wait until the cabin is warm.",
            )
        return ActionResult.success_result(
            feedback=(
                "The white enamel mug is yours, brought from Rovaniemi. It has no chip."
            ),
        )
    stage = ws.reunion_stage
    if stage in ("arrival", "tended"):
        return ActionResult.authored(
            feedback=(
                "The mug sits on the table. You haven't even sat down properly. "
                "Nika is still moving around you, deciding things. Later."
            ),
        )
    if stage == "seated":
        # The first-mouthful beat. This is the emotional weight of the
        # reunion landing: coffee in the blue mug, made exactly how
        # she takes it. Completing the reunion opens the sensory tells.
        ws.transition_reunion_to("complete")
        fear.shift(ctx.player, fear.REUNION_COMPLETE)
        return ActionResult.authored(
            feedback=(
                "You lift the mug and have your lips on the rim before you see "
                "what you are holding.\n"
                "Blue enamel. The chip in the rim, worn smooth, at the two "
                "o'clock of the handle. Your thumb goes to the chip on its own, "
                "as it has gone there through every summer of your childhood.\n"
                "The coffee is pale with milk, no sugar, made in the wide-bottomed "
                "pour your grandmother's pot demanded, the way you take it. The "
                "first mouthful tastes of being twelve years old with lake water "
                "in your hair.\n"
                "This is what you walked away from. Someone who knows the chip in "
                "the rim, which side you bruise easiest, how much silence you need "
                "before you can talk. Your eyes sting. You keep them down until it passes.\n"
                "The hook by the stove was empty last night. The thought lifts its "
                "head, but the coffee is warm and made for you without asking, "
                "because Nika has never had to ask. You put it with the concussion."
            ),
        )
    if stage in ("bedded", "night") and ws.ending == "none":
        text, _ = observe_night_seam(ws, AnomalyID.MUG_IMPOSSIBLE, ctx.player)
        return ActionResult.authored(
            feedback=text,
        )
    if stage == "dawn" and ws.ending == "none":
        # Drinking the offered coffee is the consent ending. The authored
        # beat lives in AcceptAction; route through it so the prose has one
        # home.
        from game.actions.accept import AcceptAction

        return AcceptAction().execute(ctx)
    if stage == "consented":
        return ActionResult.authored(
            feedback=(
                "The blue mug stands rinsed by the sink. Nika stacks the fire for "
                "the night. You can still taste the coffee."
            ),
        )
    if stage != "complete":
        return ActionResult.authored(
            feedback="You leave the blue mug where it is.",
        )
    return _observe_tell(
        player=ctx.player,
        anomaly=AnomalyID.KNUCKLES_BIRCH,
        world_state=ws,
    )


def use_nika(ctx: ActionContext, _item: Item) -> ActionResult:
    """Advance or observe Nika through the false-cabin reunion."""
    ws = ctx.world_state
    if not ws.is_wrong_layer():
        return ActionResult.authored(
            feedback="Nika isn't here.",
        )
    if ws.ending == "escaped":
        return ActionResult.authored(
            feedback=(
                "You do not look at what is standing by the stove in Nika's "
                "fleece. Whatever is under the face has never once been shown to "
                "you. You keep it that way."
            ),
        )
    stage = ws.reunion_stage
    if stage == "arrival":
        # She crosses, grips Elli's arm, and the lie lands. Advance to
        # 'tended': the care sequence.
        ws.transition_reunion_to("tended")
        fear.shift(ctx.player, fear.REUNION_TENDED)
        return ActionResult.authored(
            feedback=(
                "She crosses the three steps before you have answered. Her grip "
                "on your arm is solid, warm through the torn sleeve. Too firm to "
                "be anything but actual.\n"
                "\"Sit down. Sit. Look at me.\"\n"
                "\"You called me,\" she says, turning to the stove, lifting the "
                "kettle. \"So I drove up. Door was open, place was warm, no Elli. "
                "Twenty minutes I've been sitting here deciding whether to go out "
                "looking and lose the light. Then you come through the door like "
                "a shot elk.\"\n"
                "I didn't call you. The sentence forms somewhere far back in the "
                "fog and does not make it forward. Perhaps you called from the "
                "treeline. Perhaps the phone found its one bar when it mattered. "
                "The kettle is already hissing, and the thought sinks under the "
                "sound.\n"
                "She crouches in front of you with a warmed towel and cleans "
                "your face, chin steadied between finger and thumb. Follow the "
                "finger. Look at me. How many."
            ),
        )
    if stage == "tended":
        # The verdict, and the chair. Advance to 'seated'; the mug arrives
        # with the beat.
        ws.transition_reunion_to("seated")
        fear.shift(ctx.player, fear.REUNION_SEATED)
        return ActionResult.authored(
            feedback=(
                "She presses along your cheekbone and down the line of your ribs, "
                "and you hiss, and she sits back on her heels.\n"
                "\"Nothing's moving that shouldn't. Your head took a knock and "
                "your ribs are cracked or bruised, and either way you're not "
                "walking anywhere tonight.\" She says it to the fire, already "
                "deciding the evening. \"First light, we walk out together. Now "
                "drink that.\"\n"
                "She presses you into the chair by the fire, and the mug finds "
                "its way onto the table in front of you, steam rising."
            ),
        )
    if stage == "seated":
        return ActionResult.authored(
            feedback=(
                "Nika nods at the mug. \"Drink. Then tell me.\" The order is "
                "familiar enough that you obey it without yet moving."
            ),
        )
    if stage == "consented":
        return ActionResult.authored(
            feedback=(
                "\"First light,\" she says again, without looking up from the "
                "fire. \"Sleep first.\" The spare mattress is already down by "
                "the narrow bed."
            ),
        )
    if stage in ("bedded", "night"):
        return ActionResult.authored(
            feedback=(
                "She lies between you and the door, where she has always lived. "
                "You keep your own breath slow and say nothing into the dark."
            ),
        )
    if stage == "dawn":
        return ActionResult.authored(
            feedback=(
                "It holds the mug out to you. The face makes Nika's morning "
                "face and keeps making it. \"You'll want something in you,\" it "
                "says. Nika's cadence, exact. \"It's a long walk on the compass.\""
            ),
        )
    return _observe_tell(
        player=ctx.player,
        anomaly=AnomalyID.DELAYED_SMILE,
        world_state=ws,
    )


def use_mattress(ctx: ActionContext, _item: Item) -> ActionResult:
    """Land the false-cabin bed beat or narrate its unavailable states."""
    ws = ctx.world_state
    if not ws.is_wrong_layer():
        return ActionResult.success_result(
            feedback=(
                "The chest holds the spare mattress it has always held. "
                "No reason to drag it out now."
            ),
        )
    if ws.reunion_stage == "consented":
        ws.transition_reunion_to("bedded")
        fear.shift(ctx.player, fear.BEDDED)
        log_tell(ws, AnomalyID.MEMORY_ALOUD, ctx.player)
        bed_text = (
            "Nika lays the spare mattress by the narrow bed and shakes a "
            "blanket over it. Forty summers settle into place: you take the "
            "bed, I'm nearer the fire. With the lamp down, the room closes "
            "around you like a tent. You are against the wall and Nika is "
            "between you and the door, where she has always lived.\n"
            "\"Like when we were kids,\" she says, and turns down the lamp.\n\n"
            "You lie under the heavy covers with your ribs aching in their "
            "slow tide and watch the firelight move on the boards of the "
            "ceiling. The wind does not blow. The trees do not creak. Cold "
            "presses up beneath the warm room, and the room holds.\n"
            "\"You remember running to the lake,\" she says in the dark. Not "
            "a question. \"You'd go in front, with the towel round your neck. "
            "Every time. And you never once looked back to see if I was "
            "coming.\" A log settles. \"You knew I'd be there. That was the "
            "thing. You never had to look, your whole life, because I was "
            "always going to be there.\"\n\n"
            "The memory is true and belongs to you both: the pale path, the "
            "fish-smell of the lake at dusk, the towel. Nika would die before "
            "saying any of this aloud. You have watched her fail to say things "
            "all your life. It is one of the loves between you, the words put "
            "down and carried instead. Yet here is the inside of her, the "
            "grief she counted in private, spoken in her easy voice as if it "
            "cost nothing. You have wanted to hear it for twenty years.\n"
            "\"Night, Elli,\" she says.\n"
            "\"Night.\""
        )
        # MEMORY_ALOUD is a night seam; if the log is already at the
        # threshold (dev seed, replayed save), the knowing finishes here
        # rather than waiting for the next observation.
        scene = maybe_finish_the_knowing(ws, ctx.player)
        return ActionResult.authored(
            feedback=bed_text + ("\n\n" + scene if scene else ""),
        )
    if ws.reunion_stage in ("bedded", "night"):
        return ActionResult.authored(
            feedback=(
                "You are already under the covers. Nika lies on the mattress "
                "below, between you and the door."
            ),
        )
    return ActionResult.authored(
        feedback=(
            "The chest sits where it has always sat. Sleep is not the shape "
            "of this hour yet."
        ),
    )


def use_tins(ctx: ActionContext, _item: Item) -> ActionResult:
    """Observe the tins as a real fixture or false-cabin night seam."""
    ws = ctx.world_state
    if not ws.is_wrong_layer():
        return ActionResult.success_result(
            feedback="Tinned food in the cupboard. Yours, bought in Rovaniemi.",
        )
    if ws.reunion_stage in ("bedded", "night") and ws.ending == "none":
        text, _ = observe_night_seam(ws, AnomalyID.WRONG_TINS, ctx.player)
        return ActionResult.authored(
            feedback=text,
        )
    return ActionResult.authored(
        feedback=(
            "Tins, stacked by the stove. Dinner made from them was better than "
            "you would have made of them. You let the thought pass."
        ),
    )
