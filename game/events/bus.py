"""Simple synchronous pub/sub event bus."""

from __future__ import annotations

from collections import defaultdict
from typing import Callable, Dict, List, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from game.events.types import GameEvent


# Type alias for event handlers
EventHandler = Callable[["GameEvent"], None]


class EventBus:
    """
    Simple synchronous pub/sub event bus.
    
    Handlers are called immediately when events are emitted.
    Events are dispatched by their class name.
    """
    
    def __init__(self) -> None:
        self._handlers: Dict[str, List[EventHandler]] = defaultdict(list)
    
    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        """
        Subscribe a handler to an event type.
        
        Args:
            event_type: The name of the event type (e.g., "PlayerMovedEvent")
            handler: A callable that takes a GameEvent and returns None
        """
        self._handlers[event_type].append(handler)
    
    def unsubscribe(self, event_type: str, handler: EventHandler) -> None:
        """
        Unsubscribe a handler from an event type.
        
        Args:
            event_type: The name of the event type
            handler: The handler to remove
        """
        if event_type in self._handlers:
            try:
                self._handlers[event_type].remove(handler)
            except ValueError:
                pass  # Handler not found, ignore
    
    def emit(self, event: "GameEvent") -> None:
        """
        Emit an event to all subscribed handlers.
        
        Handlers are called synchronously in subscription order.
        
        Args:
            event: The event to emit
        """
        event_type = type(event).__name__
        for handler in self._handlers.get(event_type, []):
            handler(event)
    
    def clear(self) -> None:
        """Remove all handlers."""
        self._handlers.clear()
    
    @property
    def handler_count(self) -> int:
        """Total number of registered handlers."""
        return sum(len(handlers) for handlers in self._handlers.values())
