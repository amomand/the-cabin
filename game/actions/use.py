"""Use action for using items."""

from __future__ import annotations

from game.actions.base import Action, ActionContext, ActionResult


class UseAction(Action):
    """Handle using items."""
    
    @property
    def name(self) -> str:
        return "use"
    
    def execute(self, ctx: ActionContext) -> ActionResult:
        item_name = ctx.args.get("item")
        
        if not item_name:
            return ActionResult.failure_result(ctx.ai_reply or "Use what?")
        
        # Check inventory first, then the current room for non-carryable fixtures
        # (bed, sauna stove, camera feed, light switch, fireplace, breaker).
        item = ctx.player.get_item(item_name)
        if not item:
            item = ctx.room.get_item(item_name)
        if not item:
            clean_name = ctx.player._clean_item_name(item_name)
            return ActionResult.failure_result(
                ctx.ai_reply or f"You don't have a {clean_name} to use."
            )
        
        item_lower = item.name.lower()

        # Phone - play Nika's voicemail (requires some calm to actually hear it:
        # Elli only checks her phone once settled in)
        if item_lower == "phone":
            if not ctx.world_state.get("fire_lit", False):
                return ActionResult.success_result(
                    feedback=ctx.ai_reply or (
                        "You pull out the phone, then stop. Not yet. You're still in coat and cold. "
                        "Settle the cabin first."
                    ),
                    events=["use_phone_too_early"],
                    state_changes={"item_name": item.name},
                )
            if ctx.world_state.get("voicemail_heard", False):
                return ActionResult.success_result(
                    feedback=ctx.ai_reply or (
                        "You hold the phone a moment longer than you need to. "
                        "Nika's voicemail sits there, already heard, already refusing to go quiet."
                    ),
                    events=["use_phone_again"],
                    state_changes={"item_name": item.name},
                )
            ctx.world_state["voicemail_heard"] = True
            return ActionResult.success_result(
                feedback=ctx.ai_reply or (
                    "You open the voicemail. Nika's voice. Terse, strained, not hers.\n"
                    "\"Elli. It's me. You need to come home. Something's wrong with the cabin. "
                    "Not broken-wrong. Worse. It's... lying out there. Waiting.\"\n"
                    "You play it twice. The word waiting settles in the room with you."
                ),
                events=["voicemail_heard"],
                state_changes={"item_name": item.name, "voicemail_heard": True},
            )

        # Camera feed monitor - review the five-frame sequence
        if item_lower == "camera feed":
            if ctx.world_state.get("footage_reviewed", False):
                return ActionResult.success_result(
                    feedback=ctx.ai_reply or (
                        "You scroll back to the same five frames. They have not changed. "
                        "You already knew that. You look anyway."
                    ),
                    events=["use_footage_again"],
                    state_changes={"item_name": item.name},
                )
            ctx.world_state["footage_reviewed"] = True
            return ActionResult.success_result(
                feedback=ctx.ai_reply or (
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
                    feedback=ctx.ai_reply or (
                        "The stones are still warm. You don't need it again. "
                        "The place has already done what it came to do."
                    ),
                    events=["use_sauna_again"],
                    state_changes={"item_name": item.name},
                )
            ctx.world_state["sauna_used"] = True
            return ActionResult.success_result(
                feedback=ctx.ai_reply or (
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
                    feedback=ctx.ai_reply or (
                        "You look at the bed. Not now. The morning is waiting outside, and so is something else."
                    ),
                    events=["use_bed_again"],
                    state_changes={"item_name": item.name},
                )
            if not ctx.world_state.get("fire_lit", False):
                return ActionResult.success_result(
                    feedback=ctx.ai_reply or (
                        "The bed is cold. The cabin is colder. Build a fire first, "
                        "or you'll lie awake all night listening to the house remember itself."
                    ),
                    events=["use_bed_too_cold"],
                    state_changes={"item_name": item.name},
                )
            if not ctx.world_state.get("voicemail_heard", False) or not ctx.world_state.get("footage_reviewed", False):
                return ActionResult.success_result(
                    feedback=ctx.ai_reply or (
                        "You sit on the edge of the bed and stop. There's something you haven't done yet. "
                        "The phone. The feeds. You get up again."
                    ),
                    events=["use_bed_unfinished"],
                    state_changes={"item_name": item.name},
                )
            ctx.world_state["first_morning"] = True
            return ActionResult.success_result(
                feedback=ctx.ai_reply or (
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
                    feedback=ctx.ai_reply or "You flip the switch, but nothing happens. The cabin remains dark.",
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
                    feedback=ctx.ai_reply or "The fireplace is cold and empty. You need fuel to start a fire.",
                    events=["use_fireplace_no_fuel"],
                    state_changes={"item_name": item.name}
                )
        
        # Act III tells - observable only in the wrong layer.
        if item_lower == "window":
            if not ctx.world_state.get("world_layer", "real") == "wrong":
                return ActionResult.success_result(
                    feedback=ctx.ai_reply or "You glance out the window. The clearing. The treeline. Home.",
                    events=["use_window"],
                    state_changes={"item_name": item.name},
                )
            ctx.world_state.wrongness.add(
                "frost_wood_grain",
                "frost on the window, patterned like wood grain with growth rings spreading outward",
            )
            return ActionResult.success_result(
                feedback=ctx.ai_reply or (
                    "Frost is forming on the inside of the glass. It patterns itself in wood grain. "
                    "Growth rings, spreading from some unseen centre. You watch for a long moment. "
                    "Then you turn away."
                ),
                events=["use_window", "wrongness_observed"],
                state_changes={"item_name": item.name, "anomaly": "frost_wood_grain"},
            )

        if item_lower == "mug":
            if not ctx.world_state.get("world_layer", "real") == "wrong":
                return ActionResult.success_result(
                    feedback=ctx.ai_reply or "A plain enamel mug. Warm tea. You sip.",
                    events=["use_mug"],
                    state_changes={"item_name": item.name},
                )
            ctx.world_state.wrongness.add(
                "knuckles_birch",
                "Nika's hand on the mug - knuckles like knots in birch wood",
            )
            return ActionResult.success_result(
                feedback=ctx.ai_reply or (
                    "You raise the mug. Nika sets hers down. For a second her knuckles are not knuckles. "
                    "Knots in birch. The skin is bark. The joints do not bend the way joints bend.\n"
                    "Then she picks up the mug again and her hand is her hand."
                ),
                events=["use_mug", "wrongness_observed"],
                state_changes={"item_name": item.name, "anomaly": "knuckles_birch"},
            )

        if item_lower == "nika":
            if not ctx.world_state.get("world_layer", "real") == "wrong":
                return ActionResult.success_result(
                    feedback=ctx.ai_reply or "Nika isn't here.",
                    events=["use_nika"],
                    state_changes={"item_name": item.name},
                )
            ctx.world_state.wrongness.add(
                "delayed_smile",
                "Nika's smile, laid across the face a fraction late",
            )
            return ActionResult.success_result(
                feedback=ctx.ai_reply or (
                    "You say something. A small thing. Something that should have made her laugh.\n"
                    "The smile arrives. Correct. Warm. A fraction late. As if laid across the face, "
                    "rather than pulled up from underneath.\n"
                    "She meets your eyes. Holds them. Waits for you to look away."
                ),
                events=["use_nika", "wrongness_observed"],
                state_changes={"item_name": item.name, "anomaly": "delayed_smile"},
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
            "There's no circuit breaker here to use."
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
                ctx.ai_reply or "There's no light switch here."
            )
        
        if ctx.world_state.get("has_power", False):
            return ActionResult.success_result(
                feedback=ctx.ai_reply or "The lights flicker on, filling the cabin with warm illumination.",
                events=["lights_on"],
                state_changes={}
            )
        
        return ActionResult.success_result(
            feedback=ctx.ai_reply or "The light switch is unresponsive; the room remains shrouded in darkness.",
            events=["use_light_switch_no_power"],
            state_changes={}
        )
