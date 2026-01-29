"""Event type definitions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class GameEvent:
    """Base class for all game events."""
    pass


@dataclass
class PlayerMovedEvent(GameEvent):
    """Emitted when the player moves to a new room."""
    from_room_id: str
    to_room_id: str
    direction: str


@dataclass
class ItemTakenEvent(GameEvent):
    """Emitted when the player picks up an item."""
    item_name: str
    room_id: str


@dataclass
class ItemDroppedEvent(GameEvent):
    """Emitted when the player drops an item."""
    item_name: str
    room_id: str


@dataclass
class ItemThrownEvent(GameEvent):
    """Emitted when the player throws an item."""
    item_name: str
    target: Optional[str] = None
    into_darkness: bool = False


@dataclass
class PowerRestoredEvent(GameEvent):
    """Emitted when power is restored to the cabin."""
    pass


@dataclass
class FireLitEvent(GameEvent):
    """Emitted when a fire is successfully lit."""
    pass


@dataclass
class FireAttemptEvent(GameEvent):
    """Emitted when player attempts to light fire without fuel."""
    has_fuel: bool = False
    has_matches: bool = False


@dataclass
class LightSwitchUsedEvent(GameEvent):
    """Emitted when player uses a light switch."""
    has_power: bool = False


@dataclass
class FireplaceUsedEvent(GameEvent):
    """Emitted when player interacts with fireplace."""
    has_fuel: bool = False


@dataclass
class WildlifeProvokedEvent(GameEvent):
    """Emitted when wildlife is provoked."""
    wildlife_name: str
    action: str  # "attack", "flee", "wander", "ignore"
    health_damage: int = 0
    fear_increase: int = 0


@dataclass
class FuelGatheredEvent(GameEvent):
    """Emitted when player gathers fuel (firewood)."""
    item_name: str


@dataclass
class QuestTriggeredEvent(GameEvent):
    """Emitted when a quest is triggered."""
    quest_id: str
    trigger_type: str
    trigger_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class QuestUpdatedEvent(GameEvent):
    """Emitted when a quest is updated."""
    event_name: str
    event_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class QuestCompletedEvent(GameEvent):
    """Emitted when a quest is completed."""
    quest_id: str
