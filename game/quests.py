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
            "You won't last the night like this. The breaker first, then a fire. "
            "Your body has already decided, even as your mind catches up."
        ),
        objective="Restore power and warmth to the cabin by flipping the main circuit breaker and lighting a fire.",
        trigger_conditions=[
            {"type": "location", "room_id": "lakeside"},
            {"type": "action", "action": "light_fire"},
            {"type": "action", "action": "turn_on_lights"},
            {"type": "action", "action": "use_light_switch"},
            {"type": "action", "action": "use_fireplace"},
            {"type": "action", "action": "use_circuit_breaker"},
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
        completion_text="The cabin hums with life again. Warmth creeps back into your limbs.",
        quest_screen_text=(
            "The cold won't keep. Power first, then warmth.\n"
            "The breaker is in the konttori. There's wood down by the lakeside. The hearth is laid and waiting.\n\n"
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
