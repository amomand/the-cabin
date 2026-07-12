"""Use action for using items."""

from __future__ import annotations

from game.actions.base import Action, ActionContext, ActionResult
from game.story import AnomalyID, log_tell, maybe_finish_the_knowing


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
        event: str,
        narration: str,
    ) -> ActionResult:
        """Log an Act III tell and emit the authored narration.

        Tells are observed once; re-using the item in the wrong layer still
        narrates the tell but doesn't double-log it.
        """
        log_tell(world_state, anomaly)
        return ActionResult.success_result(
            feedback=narration,
            events=[event, "wrongness_observed"],
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
            ws = ctx.world_state
            if ws.is_wrong_layer():
                if ws.reunion_stage in ("bedded", "night") and ws.ending == "none":
                    log_tell(ws, AnomalyID.PHONE_DARK)
                    text = (
                        "You lie a long while before you ease out from under the covers "
                        "and cross to your jacket on the peg, one held breath at a time. "
                        "The screen will not wake. Not flat-battery dark. Dark all "
                        "through, like the sky over the clearing."
                    )
                    scene = maybe_finish_the_knowing(ws)
                    return ActionResult.success_result(
                        feedback=text + ("\n\n" + scene if scene else ""),
                        events=["use_phone_dark", "wrongness_observed"],
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
                if ws.coda_stage == "home":
                    ws.coda_stage = "called"
                    return ActionResult.success_result(
                        feedback=(
                            "You go to the window and hold the phone to the glass until "
                            "the single bar surfaces, and ring Nika.\n"
                            "It rings four times. Long enough to see yourself in the dark "
                            "of the enamel sink, one cheekbone swollen, one eye going black.\n\n"
                            "\"Elli.\"\n"
                            "And there it is. The pause. A silence with twenty years in it, "
                            "the sound of your oldest friend not knowing how to speak to "
                            "you, boots half unlaced in a doorway, both of you deciding how "
                            "to stand. Your eyes go hot with a relief you could never have "
                            "explained to anyone. The damage is in the line, real and "
                            "yours. It is the most human sound you have ever heard.\n\n"
                            "\"You went up,\" she says.\n"
                            "\"Yes.\"\n"
                            "\"Alone. I told you to wait.\"\n"
                            "\"I know.\"\n"
                            "The line hums with the distance. When she speaks again her "
                            "voice has gone quieter.\n"
                            "\"There's coffee at the shop. Come down before the light "
                            "goes. Drive slow past the lake.\"\n"
                            "\"I'm coming down,\" you say. \"Niks.\"\n"
                            "The pause this time is shorter. \"Drive slow,\" she says, and "
                            "rings off.\n\n"
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
                        "You pull out the phone, then stop. Not yet. You're still in coat and cold. "
                        "Settle the cabin first."
                    ),
                    events=["use_phone_too_early"],
                    state_changes={"item_name": item.name},
                )
            if ctx.world_state.get("voicemail_heard", False):
                return ActionResult.success_result(
                    feedback=(
                        "You hold the phone a moment longer than you need to. "
                        "Nika's voicemail sits there, already heard, already refusing to go quiet."
                    ),
                    events=["use_phone_again"],
                    state_changes={"item_name": item.name},
                )
            ctx.world_state["voicemail_heard"] = True
            return ActionResult.success_result(
                feedback=(
                    "You open the voicemail. Nika's voice. Terse, strained, not hers.\n"
                    "\"Elli. It's me. You need to come home.\"\n"
                    "\"Something's wrong with the cabin. I don't know what.\"\n"
                    "\"Don't go up on your own. Wait.\"\n"
                    "\"It's lying out there.\"\n"
                    "You play it twice. The word \"wait\" hangs in the room."
                ),
                events=["voicemail_heard"],
                state_changes={"item_name": item.name, "voicemail_heard": True},
            )

        # Camera feed monitor - review the five-frame sequence
        if item_lower == "camera feed":
            if ctx.world_state.get("footage_reviewed", False):
                return ActionResult.success_result(
                    feedback=(
                        "You scroll back to the same five frames. They have not changed. "
                        "You already knew that. You look anyway."
                    ),
                    events=["use_footage_again"],
                    state_changes={"item_name": item.name},
                )
            ctx.world_state["footage_reviewed"] = True
            return ActionResult.success_result(
                feedback=(
                    "Three feeds quiet. The northern one dead. You open the captured sequence.\n"
                    "Five frames. A tall, narrow shape at the treeline. Closer in each frame. "
                    "In the fourth, the trees behind it are not where they were in the third. "
                    "The fifth frame is black. The feed died there."
                ),
                events=["footage_reviewed"],
                state_changes={"item_name": item.name, "footage_reviewed": True},
            )

        # Sauna stove - light it and sit through the heat
        if item_lower == "sauna stove":
            if ctx.world_state.get("sauna_used", False):
                return ActionResult.success_result(
                    feedback=(
                        "The stones are still warm. You don't need it again. "
                        "The place has already done what it came to do."
                    ),
                    events=["use_sauna_again"],
                    state_changes={"item_name": item.name},
                )
            ctx.world_state["sauna_used"] = True
            return ActionResult.success_result(
                feedback=(
                    "You feed the stove and wait. The stones heat slowly. The little room glows around you. "
                    "Through the small window the lake shows between the trunks, a black plate under dusk. "
                    "For the first time since arriving, the place belongs to the part of you that loved it."
                ),
                events=["sauna_used"],
                state_changes={"item_name": item.name, "sauna_used": True},
            )

        # Bed - sleep, dream, wake to the first morning
        if item_lower == "bed":
            if ctx.world_state.get("first_morning", False):
                return ActionResult.success_result(
                    feedback=(
                        "You look at the bed. Not now. The morning is waiting outside, and so is something else."
                    ),
                    events=["use_bed_again"],
                    state_changes={"item_name": item.name},
                )
            if not ctx.world_state.get("fire_lit", False):
                return ActionResult.success_result(
                    feedback=(
                        "The bed is cold. The cabin is colder. Build a fire first, "
                        "or you'll lie awake all night listening to the house remember itself."
                    ),
                    events=["use_bed_too_cold"],
                    state_changes={"item_name": item.name},
                )
            if not ctx.world_state.get("voicemail_heard", False) or not ctx.world_state.get("footage_reviewed", False):
                return ActionResult.success_result(
                    feedback=(
                        "You sit on the edge of the bed and stop. There's something you haven't done yet. "
                        "The phone. The feeds. You get up again."
                    ),
                    events=["use_bed_unfinished"],
                    state_changes={"item_name": item.name},
                )
            ctx.world_state["first_morning"] = True
            return ActionResult.success_result(
                feedback=(
                    "You lie down under the heavy covers. Wine warmth. The smell of dry wood in the boards. "
                    "You lie awake longer than you expected. The isolation is not hostile. It is absolute.\n"
                    "You remember the scraping sound from when you were small, and the way your parents "
                    "explained it away. You tell yourself you'll check the northern edge in daylight.\n"
                    "Sleep comes. Then, later, the silence of the first morning."
                ),
                events=["first_morning"],
                state_changes={"item_name": item.name, "first_morning": True},
            )

        # Circuit breaker - restores power
        if item_lower == "circuit breaker":
            ctx.world_state["has_power"] = True
            return ActionResult.success_result(
                feedback=ctx.ai_reply or "The circuit breaker clicks into place. Power hums through the cabin.",
                events=["power_restored", "item_used"],
                state_changes={"item_name": item.name, "has_power": True}
            )
        
        # Matches with firewood - lights fire
        if item_lower == "matches" and ctx.player.has_item("firewood"):
            ctx.world_state["fire_lit"] = True
            return ActionResult.success_result(
                feedback=ctx.ai_reply or "The matches catch and the firewood ignites. Warmth spreads through the cabin.",
                events=["fire_lit", "item_used"],
                state_changes={"item_name": item.name, "fire_lit": True}
            )
        
        # Matches without firewood
        if item_lower == "matches" and not ctx.player.has_item("firewood"):
            return ActionResult.success_result(
                feedback=ctx.ai_reply or "You strike a match, but you have nothing to light.",
                events=["fire_no_fuel"],
                state_changes={"item_name": item.name}
            )
        
        # Light switch - check power
        if item_lower == "light switch":
            if ctx.world_state.get("has_power", False):
                return ActionResult.success_result(
                    feedback=ctx.ai_reply or "The light switch clicks and the cabin fills with warm light.",
                    events=["lights_on"],
                    state_changes={"item_name": item.name}
                )
            else:
                return ActionResult.success_result(
                    feedback=ctx.ai_reply or "You flip the switch. The cabin remains dark.",
                    events=["use_light_switch_no_power"],
                    state_changes={"item_name": item.name}
                )
        
        # Fireplace - check fuel
        if item_lower == "fireplace":
            if ctx.player.has_item("firewood"):
                return ActionResult.success_result(
                    feedback=ctx.ai_reply or "You could light a fire here if you had matches.",
                    events=["use_fireplace"],
                    state_changes={"item_name": item.name}
                )
            else:
                return ActionResult.success_result(
                    feedback=ctx.ai_reply or "The fireplace is cold and empty. Flame would have nothing to take.",
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
            if not ctx.world_state.reunion_complete():
                return ActionResult.success_result(
                    feedback=(
                        "You glance at the window. The light outside is flat and white, "
                        "with no sun in it. You don't look for long. Not yet."
                    ),
                    events=["use_window_pre_reunion"],
                    state_changes={"item_name": item.name},
                )
            return self._observe_tell(
                item=item,
                anomaly=AnomalyID.FROST_WOOD_GRAIN,
                world_state=ctx.world_state,
                event="use_window",
                narration=(
                    "Frost is forming on the inside of the glass. It patterns itself in wood grain. "
                    "Growth rings, spreading from some unseen centre. You watch for a long moment. "
                    "Then you turn away."
                ),
            )

        if item_lower == "mug":
            ws = ctx.world_state
            if not ws.is_wrong_layer():
                return ActionResult.success_result(
                    feedback="A plain enamel mug. Warm tea. You sip.",
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
                return ActionResult.success_result(
                    feedback=(
                        "You lift the mug and have your lips on the rim before you see "
                        "what you are holding.\n"
                        "Blue enamel. The chip in the rim, worn smooth, at the two "
                        "o'clock of the handle. Your thumb goes to the chip on its own, "
                        "as it has gone there through every summer of your childhood.\n"
                        "The coffee is pale with milk, no sugar, made in the wide-bottomed "
                        "pour your grandmother's pot demanded. Exactly, precisely how you "
                        "take it. The first mouthful is the exact taste of being twelve "
                        "years old with lake water in your hair. Your eyes sting. You "
                        "keep them down until it passes.\n"
                        "The hook by the stove was empty last night. The thought lifts "
                        "its head somewhere in the fog, and sinks under the warmth, and "
                        "does not come up again. Not yet."
                    ),
                    events=["use_mug", "reunion_complete"],
                    state_changes={
                        "item_name": item.name,
                        "reunion_stage": "complete",
                    },
                )
            if stage in ("bedded", "night") and ws.ending == "none":
                log_tell(ws, AnomalyID.MUG_IMPOSSIBLE)
                text = (
                    "The blue mug sits rinsed by the sink, whole, its chip at the two "
                    "o'clock of the handle. You drank from it tonight without thinking.\n"
                    "The hook by the stove was empty last night. You stood in front of "
                    "it. You opened the cupboard. There was no mug anywhere in this "
                    "cabin, and tonight it was here, waiting, made right, without asking."
                )
                scene = maybe_finish_the_knowing(ws)
                return ActionResult.success_result(
                    feedback=text + ("\n\n" + scene if scene else ""),
                    events=["use_mug", "wrongness_observed"],
                    state_changes={"item_name": item.name, "anomaly": AnomalyID.MUG_IMPOSSIBLE.value},
                )
            if stage == "dawn" and ws.ending == "none":
                # Drinking the offered coffee is the consent ending. The
                # authored beat lives in AcceptAction; route through it so
                # the prose has one home.
                from game.actions.accept import AcceptAction

                return AcceptAction().execute(ctx)
            # stage == "complete"
            return self._observe_tell(
                item=item,
                anomaly=AnomalyID.KNUCKLES_BIRCH,
                world_state=ws,
                event="use_mug",
                narration=(
                    "You raise the mug. Nika sets hers down. For a second her knuckles are not knuckles. "
                    "Knots in birch. The skin is bark. The joints do not bend the way joints bend.\n"
                    "Then she picks up the mug again and her hand is her hand."
                ),
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
                return ActionResult.success_result(
                    feedback=(
                        "She is on you before you have answered. Her grip on your arm is "
                        "solid. Warm through the torn sleeve. Too firm to be anything but "
                        "actual.\n"
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
                        "She is watching you. Waiting for you to say it. You don't have the words yet. "
                        "The mug is there. She nods at it without speaking. Drink first. Then tell me."
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
                anomaly=AnomalyID.DELAYED_SMILE,
                world_state=ws,
                event="use_nika",
                narration=(
                    "You say something. A small thing. Something that should have made her laugh.\n"
                    "The smile arrives. Correct. Warm. A fraction late. As if laid across the face, "
                    "rather than pulled up from underneath.\n"
                    "She meets your eyes. Holds them. Waits for you to look away."
                ),
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
                log_tell(ws, AnomalyID.MEMORY_ALOUD)
                return ActionResult.success_result(
                    feedback=(
                        "The whole arrangement assembles itself out of forty summers of "
                        "habit. You take the bed, I'm nearer the fire. The room like a "
                        "tent around the two of you. It has been the geography of every "
                        "childhood night here: you against the wall, Nika between you "
                        "and the door, because Nika is between everyone and the door. It "
                        "is where she lives.\n"
                        "\"Like when we were kids,\" she says, and turns down the lamp.\n\n"
                        "You lie under the heavy covers with your ribs aching in their "
                        "slow tide and watch the firelight move on the boards of the "
                        "ceiling.\n"
                        "\"You remember running to the lake,\" she says in the dark. Not "
                        "a question. \"You'd go in front, with the towel round your neck. "
                        "Every time. And you never once looked back to see if I was "
                        "coming.\" A log settles. \"You knew I'd be there. That was the "
                        "thing. You never had to look, your whole life, because I was "
                        "always going to be there.\"\n\n"
                        "It is a true memory, and it is yours as much as hers. But it is "
                        "not a thing Nika would say. It is a thing Nika would die before "
                        "saying. What you have just heard is the inside of her, the "
                        "tender counted grief of her, spoken aloud in her easy voice as "
                        "if it cost nothing. Offered to you like the coffee. Exactly "
                        "what you wanted, made without asking.\n"
                        "\"Night, Elli,\" she says.\n"
                        "\"Night.\""
                    ),
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
                        "You are already lying in the dark, listening. The mattress "
                        "below you holds its shape and its breathing."
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
                log_tell(ws, AnomalyID.WRONG_TINS)
                text = (
                    "Dinner, late: tins you never bought, from a cupboard that holds no "
                    "wine, though your own bottle stands corked on a counter somewhere "
                    "south of this room. You went through the shelf in your head twice. "
                    "There is no wine anywhere in this cabin. There has never been "
                    "anything in this cabin except what it needed to hold tonight."
                )
                scene = maybe_finish_the_knowing(ws)
                return ActionResult.success_result(
                    feedback=text + ("\n\n" + scene if scene else ""),
                    events=["use_tins", "wrongness_observed"],
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
            ctx.world_state["has_power"] = True
            return ActionResult.success_result(
                feedback="With a satisfying thunk, the circuit breaker clicks into place. A low hum stirs in the walls.",
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
        
        if ctx.world_state.get("has_power", False):
            return ActionResult.success_result(
                feedback=ctx.ai_reply or "The lights flicker on, filling the cabin with warm illumination.",
                events=["lights_on"],
                state_changes={}
            )
        
        return ActionResult.success_result(
            feedback=ctx.ai_reply or "The switch gives under your finger. Darkness stays where it is.",
            events=["use_light_switch_no_power"],
            state_changes={}
        )
