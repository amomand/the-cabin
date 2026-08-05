from game.quest import Quest, QuestManager


def create_warm_up_quest() -> Quest:
    """Create the Warm Up quest."""
    
    def completion_condition(player, world_state):
        """Check if both power is restored and fire is lit."""
        return world_state.get("has_power", False) and world_state.get("fire_lit", False)
    
    def fire_no_fuel_trigger(event_data, player, world_state):
        """Trigger when player tries to light fire without fuel."""
        return event_data.get("action") == "light_fire" and not player.has_item("firewood")
    
    def fire_success_trigger(event_data, player, world_state):
        """Trigger when fire is successfully lit."""
        return event_data.get("action") == "light_fire" and event_data.get("success", False)
    
    return Quest(
        quest_id="warm_up",
        title="Warm Up",
        opening_text=(
            "The lights don't respond. The hearth is cold.\n"
            "No power. No warmth. The cabin breathes its chill into your hands.\n\n"
            "Your breath is going up in front of you, indoors. "
            "That is the whole of it, and you know what it means."
        ),
        objective="Restore power and warmth to the cabin by flipping the main circuit breaker and lighting a fire.",
        # Walking into the cold room is what opens this. The old conditions were
        # `light_fire` and `turn_on_lights`, which the quest listener also
        # checks on the *success* paths (FireLitEvent, PowerRestoredEvent) --- so
        # flipping the breaker printed an overlay telling Elli the lights don't
        # respond, at the exact moment she restored them. A beat that completes
        # half the quest must never be the beat that opens it.
        #
        # `use_fireplace` stays as the one action condition: it only reaches
        # `_check_triggers` from the no-fuel failure path, which is the cabin
        # refusing her rather than answering her.
        trigger_conditions=[
            {"type": "location", "room_id": "cabin_main"},
            {"type": "action", "action": "use_fireplace"},
        ],
        update_events={
            "fire_no_fuel": {
                "trigger": fire_no_fuel_trigger,
                "text": "You have no fuel."
            },
            "fire_success": {
                "trigger": fire_success_trigger,
                "text": "The fire crackles softly, shadows dancing against the log walls. It's warm now."
            },
            "power_restored": {
                "trigger": lambda event_data, player, world_state: event_data.get("action") == "use_circuit_breaker",
                "text": "Power hums through the cabin. The lights should work now."
            },
            "fuel_gathered": {
                "trigger": lambda event_data, player, world_state: event_data.get("action") == "take_firewood",
                "text": "You now have firewood to burn."
            }
        },
        completion_condition=completion_condition,
        # Written for both halves, because completion needs both. The old line
        # ("The cabin hums with life again") described electrical restoration
        # and landed on whichever beat came second, so lighting a fire printed
        # a sentence about the mains.
        completion_text=(
            "Light and heat, and the cabin stops taking from you. "
            "Your fingers come back first, then your face. You had not noticed how held you were."
        ),
        quest_screen_text=(
            "The cold won't keep.\n"
            "The breaker is in the konttori. There's wood in the woodshed outside. The hearth is laid and waiting.\n\n"
            "Your hands know the order of it."
        )
    )


def create_quest_manager() -> QuestManager:
    """Create and configure the quest manager with all available quests."""
    manager = QuestManager()
    
    # Register the Warm Up quest
    warm_up_quest = create_warm_up_quest()
    manager.register_quest(warm_up_quest)
    
    return manager
