"""Quest event listener - handles quest triggers, updates, and completion."""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Optional

from game.events.types import (
    GameEvent,
    PlayerMovedEvent,
    ItemTakenEvent,
    PowerRestoredEvent,
    FireLitEvent,
    FireAttemptEvent,
    LightSwitchUsedEvent,
    FireplaceUsedEvent,
    FuelGatheredEvent,
)

if TYPE_CHECKING:
    from game.player import Player
    from game.world_state import WorldState


class QuestEventListener:
    """
    Listens for game events and triggers quest logic.
    
    Replaces manual _check_quest_* calls scattered throughout GameEngine.
    """
    
    def __init__(
        self,
        quest_manager,
        get_player: Callable[[], "Player"],
        get_world_state: Callable[[], "WorldState"],
        on_quest_triggered: Optional[Callable[[str], None]] = None,
        on_quest_updated: Optional[Callable[[str], None]] = None,
        on_quest_completed: Optional[Callable[[str], None]] = None,
    ):
        """
        Initialize the quest listener.
        
        Args:
            quest_manager: The quest manager instance
            get_player: Callable to get current player state
            get_world_state: Callable to get current world state
            on_quest_triggered: Callback when quest is triggered (receives opening text)
            on_quest_updated: Callback when quest is updated (receives update text)
            on_quest_completed: Callback when quest is completed (receives completion text)
        """
        self.quest_manager = quest_manager
        self.get_player = get_player
        self.get_world_state = get_world_state
        self.on_quest_triggered = on_quest_triggered
        self.on_quest_updated = on_quest_updated
        self.on_quest_completed = on_quest_completed
    
    def register(self, event_bus) -> None:
        """Register all event handlers with the event bus."""
        event_bus.subscribe("PlayerMovedEvent", self._on_player_moved)
        event_bus.subscribe("FuelGatheredEvent", self._on_fuel_gathered)
        event_bus.subscribe("PowerRestoredEvent", self._on_power_restored)
        event_bus.subscribe("FireLitEvent", self._on_fire_lit)
        event_bus.subscribe("FireAttemptEvent", self._on_fire_attempt)
        event_bus.subscribe("LightSwitchUsedEvent", self._on_light_switch_used)
        event_bus.subscribe("FireplaceUsedEvent", self._on_fireplace_used)
    
    def _check_triggers(self, trigger_type: str, trigger_data: dict) -> None:
        """Check if any quest should be triggered."""
        player = self.get_player()
        world_state = self.get_world_state()
        
        triggered_quest = self.quest_manager.check_triggers(
            trigger_type, trigger_data, player, world_state
        )
        if triggered_quest:
            self.quest_manager.activate_quest(triggered_quest)
            if self.on_quest_triggered:
                self.on_quest_triggered(triggered_quest.opening_text)
    
    def _check_updates(self, event_name: str, event_data: dict) -> None:
        """Check if any active quest should be updated."""
        player = self.get_player()
        world_state = self.get_world_state()
        
        update_text = self.quest_manager.check_updates(
            event_name, event_data, player, world_state
        )
        if update_text and self.on_quest_updated:
            self.on_quest_updated(update_text)
    
    def _check_completion(self) -> None:
        """Check if the active quest is completed."""
        player = self.get_player()
        world_state = self.get_world_state()
        
        completion_text = self.quest_manager.check_completion(player, world_state)
        if completion_text and self.on_quest_completed:
            self.on_quest_completed(completion_text)
    
    # Event handlers
    
    def _on_player_moved(self, event: PlayerMovedEvent) -> None:
        """Handle player movement - check for location-based quest triggers."""
        self._check_triggers("location", {"room_id": event.to_room_id})
    
    def _on_fuel_gathered(self, event: FuelGatheredEvent) -> None:
        """Handle fuel gathering."""
        self._check_updates("fuel_gathered", {"action": "take_firewood"})
    
    def _on_power_restored(self, event: PowerRestoredEvent) -> None:
        """Handle power restoration."""
        self._check_triggers("action", {"action": "turn_on_lights"})
        self._check_updates("power_restored", {"action": "use_circuit_breaker"})
    
    def _on_fire_lit(self, event: FireLitEvent) -> None:
        """Handle fire being lit."""
        self._check_triggers("action", {"action": "light_fire"})
        self._check_updates("fire_success", {"action": "light_fire", "success": True})
        self._check_completion()
    
    def _on_fire_attempt(self, event: FireAttemptEvent) -> None:
        """Handle fire attempt without proper items."""
        self._check_triggers("action", {"action": "light_fire"})
        self._check_updates("fire_no_fuel", {"action": "light_fire"})
    
    def _on_light_switch_used(self, event: LightSwitchUsedEvent) -> None:
        """Handle light switch use without power."""
        if not event.has_power:
            self._check_triggers("action", {"action": "turn_on_lights"})
    
    def _on_fireplace_used(self, event: FireplaceUsedEvent) -> None:
        """Handle fireplace use without fuel."""
        if not event.has_fuel:
            self._check_triggers("action", {"action": "use_fireplace"})
