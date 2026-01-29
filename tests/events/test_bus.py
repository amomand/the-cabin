"""Tests for EventBus."""

import pytest
from game.events.bus import EventBus
from game.events.types import GameEvent, PlayerMovedEvent, ItemTakenEvent


class TestEventBus:
    """Tests for EventBus."""
    
    def test_subscribe_and_emit(self):
        """Can subscribe to events and receive them."""
        bus = EventBus()
        received = []
        
        def handler(event):
            received.append(event)
        
        bus.subscribe("PlayerMovedEvent", handler)
        
        event = PlayerMovedEvent(from_room_id="a", to_room_id="b", direction="north")
        bus.emit(event)
        
        assert len(received) == 1
        assert received[0] is event
    
    def test_multiple_handlers(self):
        """Multiple handlers receive the same event."""
        bus = EventBus()
        received1 = []
        received2 = []
        
        bus.subscribe("PlayerMovedEvent", lambda e: received1.append(e))
        bus.subscribe("PlayerMovedEvent", lambda e: received2.append(e))
        
        event = PlayerMovedEvent(from_room_id="a", to_room_id="b", direction="north")
        bus.emit(event)
        
        assert len(received1) == 1
        assert len(received2) == 1
    
    def test_different_event_types(self):
        """Handlers only receive their subscribed event types."""
        bus = EventBus()
        move_events = []
        take_events = []
        
        bus.subscribe("PlayerMovedEvent", lambda e: move_events.append(e))
        bus.subscribe("ItemTakenEvent", lambda e: take_events.append(e))
        
        bus.emit(PlayerMovedEvent(from_room_id="a", to_room_id="b", direction="north"))
        bus.emit(ItemTakenEvent(item_name="rope", room_id="a"))
        
        assert len(move_events) == 1
        assert len(take_events) == 1
    
    def test_unsubscribe(self):
        """Can unsubscribe a handler."""
        bus = EventBus()
        received = []
        
        def handler(event):
            received.append(event)
        
        bus.subscribe("PlayerMovedEvent", handler)
        bus.unsubscribe("PlayerMovedEvent", handler)
        
        bus.emit(PlayerMovedEvent(from_room_id="a", to_room_id="b", direction="north"))
        
        assert len(received) == 0
    
    def test_unsubscribe_nonexistent_handler(self):
        """Unsubscribing a non-existent handler doesn't error."""
        bus = EventBus()
        
        def handler(event):
            pass
        
        # Should not raise
        bus.unsubscribe("PlayerMovedEvent", handler)
    
    def test_clear(self):
        """Can clear all handlers."""
        bus = EventBus()
        received = []
        
        bus.subscribe("PlayerMovedEvent", lambda e: received.append(e))
        bus.subscribe("ItemTakenEvent", lambda e: received.append(e))
        
        bus.clear()
        
        bus.emit(PlayerMovedEvent(from_room_id="a", to_room_id="b", direction="north"))
        bus.emit(ItemTakenEvent(item_name="rope", room_id="a"))
        
        assert len(received) == 0
    
    def test_handler_count(self):
        """Can get total handler count."""
        bus = EventBus()
        
        bus.subscribe("PlayerMovedEvent", lambda e: None)
        bus.subscribe("PlayerMovedEvent", lambda e: None)
        bus.subscribe("ItemTakenEvent", lambda e: None)
        
        assert bus.handler_count == 3
    
    def test_no_handlers_for_event(self):
        """Emitting event with no handlers doesn't error."""
        bus = EventBus()
        
        # Should not raise
        bus.emit(PlayerMovedEvent(from_room_id="a", to_room_id="b", direction="north"))
    
    def test_handler_order_preserved(self):
        """Handlers are called in subscription order."""
        bus = EventBus()
        order = []
        
        bus.subscribe("PlayerMovedEvent", lambda e: order.append(1))
        bus.subscribe("PlayerMovedEvent", lambda e: order.append(2))
        bus.subscribe("PlayerMovedEvent", lambda e: order.append(3))
        
        bus.emit(PlayerMovedEvent(from_room_id="a", to_room_id="b", direction="north"))
        
        assert order == [1, 2, 3]
