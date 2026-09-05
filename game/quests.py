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
            "The switch gives you nothing. The hearth is cold. "
            "Your breath shows in front of you. You rub your hands and turn back to the porch cupboard."
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
                "text": "The grate is bare. There is split wood in the shed."
            },
            "fire_success": {
                "trigger": fire_success_trigger,
                "text": "The first log catches. Heat begins to loosen your fingers."
            },
            "power_restored": {
                "trigger": lambda event_data, player, world_state: event_data.get("action") == "use_circuit_breaker",
                "text": "The ceiling bulb gives a weak yellow tremor. Somewhere in the wall, the fridge shudders awake."
            },
            "fuel_gathered": {
                "trigger": lambda event_data, player, world_state: event_data.get("action") == "take_firewood",
                "text": "You take the driest split logs from the stack."
            }
        },
        completion_condition=completion_condition,
        completion_text="Light and heat. You shut the porch cupboard and leave the fire to catch.",
        quest_screen_text=(
            "The breaker is in the porch cupboard. Split logs are stacked in the woodshed. The hearth is laid. "
            "Breaker. Wood. Fire. Your hands remember the order."
        )
    )


def create_quest_manager() -> QuestManager:
    """Create and configure the quest manager with all available quests."""
    manager = QuestManager()
    
    # Register the Warm Up quest
    warm_up_quest = create_warm_up_quest()
    manager.register_quest(warm_up_quest)
    
    return manager
