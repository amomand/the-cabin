"""Tests for QuestEventListener."""

import pytest
from unittest.mock import MagicMock, call

from game.events.bus import EventBus
from game.events.types import (
    PlayerMovedEvent,
    FuelGatheredEvent,
    PowerRestoredEvent,
    FireLitEvent,
    FireAttemptEvent,
    LightSwitchUsedEvent,
    FireplaceUsedEvent,
)
from game.events.listeners.quest_listener import QuestEventListener


class TestQuestEventListener:
    """Tests for QuestEventListener."""
    
    @pytest.fixture
    def mock_quest_manager(self):
        manager = MagicMock()
        manager.check_triggers.return_value = None
        manager.check_updates.return_value = None
        manager.check_completion.return_value = None
        return manager
    
    @pytest.fixture
    def mock_player(self):
        return MagicMock()
    
    @pytest.fixture
    def mock_world_state(self):
        return MagicMock()
    
    @pytest.fixture
    def listener(self, mock_quest_manager, mock_player, mock_world_state):
        return QuestEventListener(
            quest_manager=mock_quest_manager,
            get_player=lambda: mock_player,
            get_world_state=lambda: mock_world_state,
        )
    
    @pytest.fixture
    def event_bus(self):
        return EventBus()
    
    def test_register_subscribes_to_events(self, listener, event_bus):
        """register() subscribes to the correct event types."""
        listener.register(event_bus)
        
        # Should have handlers registered
        assert event_bus.handler_count > 0
    
    def test_player_moved_triggers_location_check(
        self, listener, event_bus, mock_quest_manager, mock_player, mock_world_state
    ):
        """PlayerMovedEvent triggers location-based quest check."""
        listener.register(event_bus)
        
        event_bus.emit(PlayerMovedEvent(
            from_room_id="wilderness",
            to_room_id="clearing",
            direction="north"
        ))
        
        mock_quest_manager.check_triggers.assert_called_once_with(
            "location",
            {"room_id": "clearing"},
            mock_player,
            mock_world_state
        )
    
    def test_fuel_gathered_triggers_update(
        self, listener, event_bus, mock_quest_manager
    ):
        """FuelGatheredEvent triggers quest update check."""
        listener.register(event_bus)
        
        event_bus.emit(FuelGatheredEvent(item_name="firewood"))
        
        mock_quest_manager.check_updates.assert_called()
    
    def test_power_restored_triggers_update_and_trigger(
        self, listener, event_bus, mock_quest_manager
    ):
        """PowerRestoredEvent triggers both update and trigger checks."""
        listener.register(event_bus)
        
        event_bus.emit(PowerRestoredEvent())
        
        mock_quest_manager.check_triggers.assert_called()
        mock_quest_manager.check_updates.assert_called()
    
    def test_fire_lit_triggers_completion_check(
        self, listener, event_bus, mock_quest_manager
    ):
        """FireLitEvent triggers quest completion check."""
        listener.register(event_bus)
        
        event_bus.emit(FireLitEvent())
        
        mock_quest_manager.check_completion.assert_called()
    
    def test_quest_triggered_callback(
        self, mock_quest_manager, mock_player, mock_world_state, event_bus
    ):
        """on_quest_triggered callback is called when quest is triggered."""
        triggered_texts = []
        
        mock_quest = MagicMock()
        mock_quest.opening_text = "A new quest begins..."
        mock_quest_manager.check_triggers.return_value = mock_quest
        
        listener = QuestEventListener(
            quest_manager=mock_quest_manager,
            get_player=lambda: mock_player,
            get_world_state=lambda: mock_world_state,
            on_quest_triggered=lambda text: triggered_texts.append(text),
        )
        listener.register(event_bus)
        
        event_bus.emit(PlayerMovedEvent(
            from_room_id="a", to_room_id="b", direction="north"
        ))
        
        assert triggered_texts == ["A new quest begins..."]
        mock_quest_manager.activate_quest.assert_called_once_with(mock_quest)
    
    def test_quest_updated_callback(
        self, mock_quest_manager, mock_player, mock_world_state, event_bus
    ):
        """on_quest_updated callback is called when quest is updated."""
        updated_texts = []
        
        mock_quest_manager.check_updates.return_value = "Progress made!"
        
        listener = QuestEventListener(
            quest_manager=mock_quest_manager,
            get_player=lambda: mock_player,
            get_world_state=lambda: mock_world_state,
            on_quest_updated=lambda text: updated_texts.append(text),
        )
        listener.register(event_bus)
        
        event_bus.emit(FuelGatheredEvent(item_name="firewood"))
        
        assert updated_texts == ["Progress made!"]
    
    def test_quest_completed_callback(
        self, mock_quest_manager, mock_player, mock_world_state, event_bus
    ):
        """on_quest_completed callback is called when quest is completed."""
        completed_texts = []
        
        mock_quest_manager.check_completion.return_value = "Quest complete!"
        
        listener = QuestEventListener(
            quest_manager=mock_quest_manager,
            get_player=lambda: mock_player,
            get_world_state=lambda: mock_world_state,
            on_quest_completed=lambda text: completed_texts.append(text),
        )
        listener.register(event_bus)
        
        event_bus.emit(FireLitEvent())
        
        assert completed_texts == ["Quest complete!"]
    
    def test_light_switch_no_power_triggers_quest(
        self, listener, event_bus, mock_quest_manager
    ):
        """LightSwitchUsedEvent without power triggers quest."""
        listener.register(event_bus)
        
        event_bus.emit(LightSwitchUsedEvent(has_power=False))
        
        mock_quest_manager.check_triggers.assert_called()
    
    def test_light_switch_with_power_no_trigger(
        self, listener, event_bus, mock_quest_manager
    ):
        """LightSwitchUsedEvent with power doesn't trigger quest."""
        listener.register(event_bus)
        
        event_bus.emit(LightSwitchUsedEvent(has_power=True))
        
        mock_quest_manager.check_triggers.assert_not_called()
    
    def test_fireplace_no_fuel_triggers_quest(
        self, listener, event_bus, mock_quest_manager
    ):
        """FireplaceUsedEvent without fuel triggers quest."""
        listener.register(event_bus)
        
        event_bus.emit(FireplaceUsedEvent(has_fuel=False))
        
        mock_quest_manager.check_triggers.assert_called()
