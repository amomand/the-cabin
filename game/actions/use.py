"""Use action for using items."""

from __future__ import annotations

from game.actions.base import Action, ActionContext, ActionResult
from game.story import (
    AnomalyID,
    fear,
    log_tell,
    maybe_finish_the_knowing,
    observe_night_seam,
)
from game.story.evening import observe_evening_through


class UseAction(Action):
    """Handle using items."""

    @property
    def name(self) -> str:
        return "use"

    @staticmethod
    def _observe_tell(
        *,
        item,
        anomaly: AnomalyID,
        world_state,
        player,
        event: str,
    ) -> ActionResult:
        """Log Act III evening beats through this tell and narrate them.

        Tells land in story order even if the fixtures are inspected out of
        order. Re-using a fixture returns its callback without double-logging.
        """
        already_seen = world_state.wrongness.has(anomaly.value)
        narration = observe_evening_through(world_state, anomaly, player)
        return ActionResult.success_result(
            feedback=narration,
            events=[event] + ([] if already_seen else ["wrongness_observed"]),
            state_changes={"item_name": item.name, "anomaly": anomaly.value},
        )
    
    def execute(self, ctx: ActionContext) -> ActionResult:
        item_name = ctx.args.get("item")
        
        if not item_name:
            return ActionResult.failure_result(
                ctx.ai_reply or "Your hand searches for something to use and finds only air."
            )
        
        # Check inventory first, then the current room for non-carryable fixtures
        # (bed, sauna stove, camera feed, light switch, fireplace, breaker).
        item = ctx.player.get_item(item_name)
        if not item:
            item = ctx.room.get_item(item_name)
        if not item:
            clean_name = ctx.player._clean_item_name(item_name)
            return ActionResult.failure_result(
                ctx.ai_reply or f"You reach for the {clean_name}, but your hand closes on empty air."
            )
        
        item_lower = item.name.lower()

        # Phone - three lives: the Act I voicemail, the dead screen in the
        # false-cabin night (a seam), and the coda phone call home.
        if item_lower == "phone":
            # Every phone path is an authored beat. The model may select the
            # action, but it must not add effects after the fixed result lands.
            ctx.intent.effects = None
            ws = ctx.world_state
            if ws.is_wrong_layer():
                if ws.reunion_stage in ("bedded", "night") and ws.ending == "none":
                    text, observed = observe_night_seam(
                        ws, AnomalyID.PHONE_DARK, ctx.player
                    )
                    return ActionResult.success_result(
                        feedback=text,
                        events=["use_phone_dark"]
                        + (["wrongness_observed"] if observed else []),
                        state_changes={"item_name": item.name, "anomaly": AnomalyID.PHONE_DARK.value},
                    )
                return ActionResult.success_result(
                    feedback=(
                        "Your phone is in your jacket on the peg by the door. Your head "
                        "is one enormous pulse. Later."
                    ),
                    events=["use_phone_wrong_layer"],
                    state_changes={"item_name": item.name},
                )
            if ws.ending == "escaped":
                # The call belongs to the cabin window and its one bar. A
                # carried phone must not fire the beat from the wrong room.
                if getattr(ctx.map.current_room, "id", None) != "cabin_main":
                    return ActionResult.success_result(
                        feedback=(
                            "No bar out here. The signal lives at the cabin "
                            "window, held to the glass, angled at the road."
                        ),
                        events=["use_phone_no_signal"],
                        state_changes={"item_name": item.name},
                    )
                if ws.coda_stage == "home":
                    ws.coda_stage = "called"
                    fear.shift(ctx.player, fear.CODA_CALLED)
                    return ActionResult.success_result(
                        feedback=(
                            "You go to the window and hold the phone to the glass until "
                            "the single bar surfaces, and ring Nika.\n"
                            "It rings four times. Long enough to see yourself in the dark "
                            "of the enamel sink, one cheekbone swollen, one eye going black.\n\n"
                            "\"Elli.\"\n"
                            "The pause holds all twenty years: your oldest friend not "
                            "knowing how to speak to you, boots half unlaced in a doorway, "
                            "both of you deciding how to stand. Your eyes go hot. The "
                            "damage is still in the line, real and yours.\n\n"
                            "\"You went up,\" she says.\n"
                            "\"Yes.\"\n"
                            "\"Alone.\" A breath goes out through the word. \"I told "
                            "you to wait.\"\n"
                            "\"I know.\"\n"
                            "The line hums with the distance, satellites and weather. "
                            "When she speaks again her voice has gone quieter, the "
                            "pricing-gun flatness with something under it that neither "
                            "of you is going to name today.\n"
                            "\"There's coffee at the shop. Come down before the light "
                            "goes. Drive slow past the lake.\"\n"
                            "\"I'm coming down,\" you say. \"Niks.\"\n"
                            "The pause this time is shorter. \"Drive slow,\" she says, and "
                            "rings off.\n\n"
                            "You stand at the window a moment longer. The clearing is "
                            "white under the first proper daylight, your tracks and the "
                            "fox's written across it. The treeline stands at the "
                            "distance it stands at today.\n"
                            "You start to pack."
                        ),
                        events=["coda_call", "use_phone"],
                        state_changes={"item_name": item.name, "coda_stage": "called"},
                    )
                if ws.coda_stage in ("called", "scraping"):
                    return ActionResult.success_result(
                        feedback=(
                            "The call is made. The shop, the coffee, the road past the "
                            "lake. The phone has done what it can do."
                        ),
                        events=["use_phone_again"],
                        state_changes={"item_name": item.name},
                    )
            if not ctx.world_state.get("fire_lit", False):
                return ActionResult.success_result(
                    feedback=(
                        "You take out the phone, but your fingers are stiff on the case. "
                        "The cold room comes first."
                    ),
                    events=["use_phone_too_early"],
                    state_changes={"item_name": item.name},
                )
            if ctx.world_state.get("voicemail_heard", False):
                return ActionResult.success_result(
                    feedback=(
                        "You do not play the message again. You can hear the pause without it."
                    ),
                    events=["use_phone_again"],
                    state_changes={"item_name": item.name},
                )
            ctx.world_state["voicemail_heard"] = True
            fear.shift(ctx.player, fear.VOICEMAIL_WARNING)
            return ActionResult.success_result(
                feedback=(
                    "You play Nika's message again. Eleven days old, every word waiting where you left it.\n"
                    "\"Elli. It's me. You need to come home. Something's wrong with the cabin. "
                    "I don't know what. Don't go up on your own. Wait. It's... it's lying out there.\"\n"
                    "The pause before the last line is the worst part. Nika does not pause."
                ),
                events=["voicemail_heard"],
                state_changes={"item_name": item.name, "voicemail_heard": True},
            )

        # Camera feed monitor - review the five-frame sequence
        if item_lower == "camera feed":
            # The model selects the action; the authored beat owns its effects.
            ctx.intent.effects = None
            if ctx.world_state.get("footage_reviewed", False):
                return ActionResult.success_result(
                    feedback=(
                        "You open the older five frames again. The forked birch is still at the right edge, "
                        "then left of centre. You look until your thumb aches."
                    ),
                    events=["use_footage_again"],
                    state_changes={"item_name": item.name},
                )
            ctx.world_state["footage_reviewed"] = True
            fear.shift(ctx.player, fear.CAMERA_FOOTAGE)
            return ActionResult.success_result(
                feedback=(
                    "Three feeds show frost and stillness. The northern one is dead. You open the saved sequence from five weeks ago.\n"
                    "Five frames. In the first, a tall, narrow shape stands at the treeline and the forked birch is at the right edge. "
                    "By the fourth, the shape is closer and the birch has moved left of centre. The ground beneath it is unmarked.\n"
                    "Frame five is black."
                ),
                events=["footage_reviewed"],
                state_changes={"item_name": item.name, "footage_reviewed": True},
            )

        # Sauna stove - light it and sit through the heat
        if item_lower == "sauna stove":
            ctx.intent.effects = None
            if ctx.world_state.get("sauna_used", False):
                return ActionResult.success_result(
                    feedback=(
                        "The stones still hold their heat. Steam lifts from the ladle and is gone."
                    ),
                    events=["use_sauna_again"],
                    state_changes={"item_name": item.name},
                )
            ctx.world_state["sauna_used"] = True
            return ActionResult.success_result(
                feedback=(
                    "You feed the stove until the stones begin to give back heat, then sit on the top bench in the dark. "
                    "Water hisses on the stones and the sound fills the little room before it fades. "
                    "For a while, the part of you that loves this place is not held at a distance."
                ),
                events=["sauna_used"],
                state_changes={"item_name": item.name, "sauna_used": True},
            )

        # Bed - sleep, dream, wake to the first morning
        if item_lower == "bed":
            ctx.intent.effects = None
            if ctx.world_state.get("first_morning", False):
                return ActionResult.success_result(
                    feedback=(
                        "You have slept enough. The morning waits outside."
                    ),
                    events=["use_bed_again"],
                    state_changes={"item_name": item.name},
                )
            if not ctx.world_state.get("fire_lit", False):
                return ActionResult.success_result(
                    feedback=(
                        "The blankets are cold through. Without a fire they will not lose it."
                    ),
                    events=["use_bed_too_cold"],
                    state_changes={"item_name": item.name},
                )
            unfinished = []
            if not ctx.world_state.get("voicemail_heard", False):
                unfinished.append("Nika's message waits on the phone.")
            if not ctx.world_state.get("footage_reviewed", False):
                unfinished.append("The saved frames are still unopened in the konttori.")
            if not ctx.world_state.get("sauna_used", False):
                unfinished.append("The sauna is still cold above the lake.")
            if unfinished:
                return ActionResult.success_result(
                    feedback=(
                        "You sit on the edge of the bed. " + " ".join(unfinished) + " You get up."
                    ),
                    events=["use_bed_unfinished"],
                    state_changes={"item_name": item.name},
                )
            ctx.world_state["first_morning"] = True
            return ActionResult.success_result(
                feedback=(
                    "You eat bread and packet soup at the square table, pour one glass of wine, and drink it. "
                    "You cork the bottle on the counter, the empty glass beside it.\n"
                    "Under the heavy covers, the isolation becomes total: the nearest lit window forty minutes south, "
                    "no signal unless you hold the phone to the glass, the dark going on over the lake and bog.\n"
                    "The fire ticks in the other room. You think of the empty hook and the scraping under the boards, "
                    "then set yourself the morning's work: the northern camera in daylight, battery, moisture, board, in that order.\n"
                    "You sleep better than you expect. You wake into silence. Then a log shifts in the hearth and puts sound back in the room. "
                    "Ten past eight and the window is still black."
                ),
                events=["first_morning"],
                state_changes={"item_name": item.name, "first_morning": True},
            )

        # Circuit breaker - restores power
        if item_lower == "circuit breaker":
            ctx.intent.effects = None
            ctx.world_state["has_power"] = True
            return ActionResult.success_result(
                feedback="The breaker takes. Somewhere beyond the wall, the fridge shudders awake.",
                events=["power_restored", "item_used"],
                state_changes={"item_name": item.name, "has_power": True}
            )
        
        # Matches with firewood - lights fire
        if item_lower == "matches" and ctx.player.has_item("firewood"):
            ctx.intent.effects = None
            ctx.world_state["fire_lit"] = True
            return ActionResult.success_result(
                feedback="The kindling catches. Heat begins at the hearth and nowhere else.",
                events=["fire_lit", "item_used"],
                state_changes={"item_name": item.name, "fire_lit": True}
            )
        
        # Matches without firewood
        if item_lower == "matches" and not ctx.player.has_item("firewood"):
            ctx.intent.effects = None
            return ActionResult.success_result(
                feedback="You strike a match, but you have nothing to light.",
                events=["fire_no_fuel"],
                state_changes={"item_name": item.name}
            )
        
        # Light switch - check power
        if item_lower == "light switch":
            ctx.intent.effects = None
            if ctx.world_state.get("has_power", False):
                return ActionResult.success_result(
                    feedback="The switch clicks. The ceiling bulb burns weak and yellow.",
                    events=["lights_on"],
                    state_changes={"item_name": item.name}
                )
            else:
                return ActionResult.success_result(
                    feedback="The switch gives under your finger. Darkness stays where it is.",
                    events=["use_light_switch_no_power"],
                    state_changes={"item_name": item.name}
                )
        
        # Fireplace - check fuel
        if item_lower == "fireplace":
            ctx.intent.effects = None
            if ctx.player.has_item("firewood"):
                return ActionResult.success_result(
                    feedback="The kindling is laid. You need the matches.",
                    events=["use_fireplace"],
                    state_changes={"item_name": item.name}
                )
            else:
                return ActionResult.success_result(
                    feedback="The grate is bare. Flame would have nothing to take.",
                    events=["use_fireplace_no_fuel"],
                    state_changes={"item_name": item.name}
                )
        
        # Act III: the wrong cabin. Tells are gated behind the reunion scene.
        # The reunion plays out in three beats: arrival (Nika on her feet),
        # seated (coffee poured, not tasted), complete (first mouthful landed).
        # Only after 'complete' do the sensory tells fire as wrongness.
        if item_lower == "window":
            if not ctx.world_state.is_wrong_layer():
                return ActionResult.success_result(
                    feedback="You glance out the window. The clearing. The treeline. Home.",
                    events=["use_window"],
                    state_changes={"item_name": item.name},
                )
            stage = ctx.world_state.reunion_stage
            if stage in ("arrival", "tended", "seated"):
                return ActionResult.success_result(
                    feedback=(
                        "You glance at the window. The light outside is flat and white, "
                        "with no sun in it. You don't look for long. Not yet."
                    ),
                    events=["use_window_pre_reunion"],
                    state_changes={"item_name": item.name},
                )
            if stage != "complete":
                return ActionResult.success_result(
                    feedback=(
                        "Beyond the glass: black ground, close trees, no sky you can use. "
                        "You stay on the warm side of it."
                    ),
                    events=["use_window_after_consent"],
                    state_changes={"item_name": item.name},
                )
            return self._observe_tell(
                item=item,
                player=ctx.player,
                anomaly=AnomalyID.FROST_WOOD_GRAIN,
                world_state=ctx.world_state,
                event="use_window",
            )

        if item_lower == "mug":
            ws = ctx.world_state
            if not ws.is_wrong_layer():
                if not ws.get("fire_lit", False) or not ws.get("has_power", False):
                    return ActionResult.success_result(
                        feedback="The hook is empty. The cupboard can wait until the cabin is warm.",
                        events=["use_mug"],
                        state_changes={"item_name": item.name},
                    )
                return ActionResult.success_result(
                    feedback=(
                        "The white enamel mug is yours, brought from Rovaniemi. It has no chip."
                    ),
                    events=["use_mug"],
                    state_changes={"item_name": item.name},
                )
            stage = ws.reunion_stage
            if stage in ("arrival", "tended"):
                return ActionResult.success_result(
                    feedback=(
                        "The mug sits on the table. You haven't even sat down properly. "
                        "Nika is still moving around you, deciding things. Later."
                    ),
                    events=["use_mug_pre_seated"],
                    state_changes={"item_name": item.name},
                )
            if stage == "seated":
                # The first-mouthful beat. This is the emotional weight of the
                # reunion landing: coffee in the blue mug, made exactly how
                # she takes it. Completing the reunion opens the sensory tells.
                ws.reunion_stage = "complete"
                fear.shift(ctx.player, fear.REUNION_COMPLETE)
                return ActionResult.success_result(
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
                    events=["use_mug", "reunion_complete"],
                    state_changes={
                        "item_name": item.name,
                        "reunion_stage": "complete",
                    },
                )
            if stage in ("bedded", "night") and ws.ending == "none":
                text, observed = observe_night_seam(
                    ws, AnomalyID.MUG_IMPOSSIBLE, ctx.player
                )
                return ActionResult.success_result(
                    feedback=text,
                    events=["use_mug"]
                    + (["wrongness_observed"] if observed else []),
                    state_changes={"item_name": item.name, "anomaly": AnomalyID.MUG_IMPOSSIBLE.value},
                )
            if stage == "dawn" and ws.ending == "none":
                # Drinking the offered coffee is the consent ending. The
                # authored beat lives in AcceptAction; route through it so
                # the prose has one home.
                from game.actions.accept import AcceptAction

                return AcceptAction().execute(ctx)
            if stage == "consented":
                return ActionResult.success_result(
                    feedback=(
                        "The blue mug stands rinsed by the sink. Nika stacks the fire for "
                        "the night. You can still taste the coffee."
                    ),
                    events=["use_mug_consented"],
                    state_changes={"item_name": item.name},
                )
            if stage != "complete":
                return ActionResult.success_result(
                    feedback="You leave the blue mug where it is.",
                    events=["use_mug_after_reunion"],
                    state_changes={"item_name": item.name},
                )
            # stage == "complete"
            return self._observe_tell(
                item=item,
                player=ctx.player,
                anomaly=AnomalyID.KNUCKLES_BIRCH,
                world_state=ws,
                event="use_mug",
            )

        if item_lower == "nika":
            ws = ctx.world_state
            if not ws.is_wrong_layer():
                return ActionResult.success_result(
                    feedback="Nika isn't here.",
                    events=["use_nika"],
                    state_changes={"item_name": item.name},
                )
            if ws.ending == "escaped":
                return ActionResult.success_result(
                    feedback=(
                        "You do not look at what is standing by the stove in Nika's "
                        "fleece. Whatever is under the face has never once been shown to "
                        "you. You keep it that way."
                    ),
                    events=["use_nika_after_refusal"],
                    state_changes={"item_name": item.name},
                )
            stage = ws.reunion_stage
            if stage == "arrival":
                # She crosses, grips Elli's arm, and the lie lands. Advance
                # to 'tended': the care sequence.
                ws.reunion_stage = "tended"
                fear.shift(ctx.player, fear.REUNION_TENDED)
                return ActionResult.success_result(
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
                    events=["use_nika", "reunion_tended"],
                    state_changes={
                        "item_name": item.name,
                        "reunion_stage": "tended",
                    },
                )
            if stage == "tended":
                # The verdict, and the chair. Advance to 'seated'; the mug
                # arrives with the beat.
                ws.reunion_stage = "seated"
                fear.shift(ctx.player, fear.REUNION_SEATED)
                return ActionResult.success_result(
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
                    events=["use_nika", "reunion_seated"],
                    state_changes={
                        "item_name": item.name,
                        "reunion_stage": "seated",
                    },
                )
            if stage == "seated":
                return ActionResult.success_result(
                    feedback=(
                        "Nika nods at the mug. \"Drink. Then tell me.\" The order is "
                        "familiar enough that you obey it without yet moving."
                    ),
                    events=["use_nika_seated"],
                    state_changes={"item_name": item.name},
                )
            if stage == "consented":
                return ActionResult.success_result(
                    feedback=(
                        "\"First light,\" she says again, without looking up from the "
                        "fire. \"Sleep first.\" The spare mattress is already down by "
                        "the narrow bed."
                    ),
                    events=["use_nika_consented"],
                    state_changes={"item_name": item.name},
                )
            if stage in ("bedded", "night"):
                return ActionResult.success_result(
                    feedback=(
                        "She lies between you and the door, where she has always lived. "
                        "You keep your own breath slow and say nothing into the dark."
                    ),
                    events=["use_nika_night"],
                    state_changes={"item_name": item.name},
                )
            if stage == "dawn":
                return ActionResult.success_result(
                    feedback=(
                        "It holds the mug out to you. The face makes Nika's morning "
                        "face and keeps making it. \"You'll want something in you,\" it "
                        "says. Nika's cadence, exact. \"It's a long walk on the compass.\""
                    ),
                    events=["use_nika_dawn"],
                    state_changes={"item_name": item.name},
                )
            # stage == "complete"
            return self._observe_tell(
                item=item,
                player=ctx.player,
                anomaly=AnomalyID.DELAYED_SMILE,
                world_state=ws,
                event="use_nika",
            )

        # The spare mattress: the bed beat of the false-cabin night.
        if item_lower == "mattress":
            ws = ctx.world_state
            if not ws.is_wrong_layer():
                return ActionResult.success_result(
                    feedback=(
                        "The chest holds the spare mattress it has always held. "
                        "No reason to drag it out now."
                    ),
                    events=["use_mattress"],
                    state_changes={"item_name": item.name},
                )
            if ws.reunion_stage == "consented":
                ws.reunion_stage = "bedded"
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
                        "cost nothing. The voice spends it as easily as the coffee, made "
                        "without asking. You have wanted to hear it for twenty years.\n"
                        "\"Night, Elli,\" she says.\n"
                        "\"Night.\""
                )
                # MEMORY_ALOUD is a night seam; if the log is already at the
                # threshold (dev seed, replayed save), the knowing finishes
                # here rather than waiting for the next observation.
                scene = maybe_finish_the_knowing(ws, ctx.player)
                return ActionResult.success_result(
                    feedback=bed_text + ("\n\n" + scene if scene else ""),
                    events=["use_mattress", "reunion_bedded", "wrongness_observed"],
                    state_changes={
                        "item_name": item.name,
                        "reunion_stage": "bedded",
                        "anomaly": AnomalyID.MEMORY_ALOUD.value,
                    },
                )
            if ws.reunion_stage in ("bedded", "night"):
                return ActionResult.success_result(
                    feedback=(
                        "You are already under the covers. Nika lies on the mattress "
                        "below, between you and the door."
                    ),
                    events=["use_mattress_night"],
                    state_changes={"item_name": item.name},
                )
            return ActionResult.success_result(
                feedback=(
                    "The chest sits where it has always sat. Sleep is not the shape "
                    "of this hour yet."
                ),
                events=["use_mattress_early"],
                state_changes={"item_name": item.name},
            )

        # The tins: dinner that was never yours. A night seam.
        if item_lower == "tins":
            ws = ctx.world_state
            if not ws.is_wrong_layer():
                return ActionResult.success_result(
                    feedback="Tinned food in the cupboard. Yours, bought in Rovaniemi.",
                    events=["use_tins"],
                    state_changes={"item_name": item.name},
                )
            if ws.reunion_stage in ("bedded", "night") and ws.ending == "none":
                text, observed = observe_night_seam(
                    ws, AnomalyID.WRONG_TINS, ctx.player
                )
                return ActionResult.success_result(
                    feedback=text,
                    events=["use_tins"]
                    + (["wrongness_observed"] if observed else []),
                    state_changes={"item_name": item.name, "anomaly": AnomalyID.WRONG_TINS.value},
                )
            return ActionResult.success_result(
                feedback=(
                    "Tins, stacked by the stove. Dinner made from them was better than "
                    "you would have made of them. You let the thought pass."
                ),
                events=["use_tins_early"],
                state_changes={"item_name": item.name},
            )

        # Generic use
        return ActionResult.success_result(
            feedback=ctx.ai_reply or f"You use the {item.name}.",
            events=["item_used"],
            state_changes={"item_name": item.name}
        )


class UseCircuitBreakerAction(Action):
    """Handle using the circuit breaker directly (room-based)."""
    
    @property
    def name(self) -> str:
        return "use_circuit_breaker"
    
    def execute(self, ctx: ActionContext) -> ActionResult:
        room = ctx.room
        
        if room.has_item("circuit breaker"):
            ctx.intent.effects = None
            ctx.world_state["has_power"] = True
            return ActionResult.success_result(
                feedback="The breaker takes. Somewhere beyond the wall, the fridge shudders awake.",
                events=["power_restored"],
                state_changes={"has_power": True}
            )
        
        return ActionResult.failure_result(
            "Your hand finds only wall and cold paint."
        )


class TurnOnLightsAction(Action):
    """Handle turning on lights."""
    
    @property
    def name(self) -> str:
        return "turn_on_lights"
    
    def execute(self, ctx: ActionContext) -> ActionResult:
        room = ctx.room
        
        if not room.has_item("light switch"):
            return ActionResult.failure_result(
                ctx.ai_reply or "Your hand searches the wall and finds no switch."
            )
        
        ctx.intent.effects = None
        if ctx.world_state.get("has_power", False):
            return ActionResult.success_result(
                feedback="The switch clicks. The ceiling bulb burns weak and yellow.",
                events=["lights_on"],
                state_changes={}
            )
        
        return ActionResult.success_result(
            feedback="The switch gives under your finger. Darkness stays where it is.",
            events=["use_light_switch_no_power"],
            state_changes={}
        )
