"""Event type definitions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


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


# --- Reserved vocabulary -------------------------------------------------
# The following item-related events are currently emitted by the engine and
# server (see game/game_engine.py and server/session.py) but have no
# subscribers yet. They are kept as forward-looking vocabulary so listeners
# (inventory analytics, Lyer reactions to handled items, etc.) can plug in
# later without touching the emit sites. Do not remove the emits or these
# classes without auditing both engine and server paths.

@dataclass
class ItemTakenEvent(GameEvent):
    """Emitted when the player picks up an item.

    Reserved: emitted by engine/server; no subscribers yet.
    """
    item_name: str
    room_id: str


@dataclass
class ItemDroppedEvent(GameEvent):
    """Emitted when the player drops an item.

    Reserved: emitted by engine/server; no subscribers yet.
    """
    item_name: str
    room_id: str


@dataclass
class ItemThrownEvent(GameEvent):
    """Emitted when the player throws an item.

    Reserved: emitted by engine/server; no subscribers yet.
    """
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
    """Emitted when wildlife is provoked.

    Reserved: emitted by engine/server; no subscribers yet. Kept as
    forward-looking vocabulary for future wildlife/fear listeners.
    """
    wildlife_name: str
    action: str  # "attack", "flee", "wander", "ignore"
    health_damage: int = 0
    fear_increase: int = 0


@dataclass
class FuelGatheredEvent(GameEvent):
    """Emitted when player gathers fuel (firewood)."""
    item_name: str
