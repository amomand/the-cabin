"""Typed requests from actions to the shared turn coordinator.

Actions mutate the world state they own directly.  These request objects cover
the smaller set of ordered effects that must be coordinated by ``game.turn``:
EventBus publication and player-stat changes shared by both surfaces.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple, Type, Union


@dataclass(frozen=True, slots=True)
class PlayerMovedRequest:
    from_room_id: str
    to_room_id: str
    direction: str


@dataclass(frozen=True, slots=True)
class ItemTakenRequest:
    item_name: str
    room_id: str


@dataclass(frozen=True, slots=True)
class FuelGatheredRequest:
    item_name: str


@dataclass(frozen=True, slots=True)
class ItemDroppedRequest:
    item_name: str
    room_id: str


@dataclass(frozen=True, slots=True)
class ItemThrownRequest:
    item_name: str
    target: Optional[str]
    into_darkness: bool


@dataclass(frozen=True, slots=True)
class DarknessFearRequest:
    increase: int


@dataclass(frozen=True, slots=True)
class PowerRestoredRequest:
    pass


@dataclass(frozen=True, slots=True)
class FireLitRequest:
    fear_reduction: int


@dataclass(frozen=True, slots=True)
class FireAttemptRequest:
    has_fuel: bool
    has_matches: bool


@dataclass(frozen=True, slots=True)
class LightSwitchUsedRequest:
    has_power: bool


@dataclass(frozen=True, slots=True)
class FireplaceUsedRequest:
    has_fuel: bool


TurnRequest = Union[
    PlayerMovedRequest,
    ItemTakenRequest,
    FuelGatheredRequest,
    ItemDroppedRequest,
    ItemThrownRequest,
    DarknessFearRequest,
    PowerRestoredRequest,
    FireLitRequest,
    FireAttemptRequest,
    LightSwitchUsedRequest,
    FireplaceUsedRequest,
]

TURN_REQUEST_TYPES: Tuple[Type[object], ...] = (
    PlayerMovedRequest,
    ItemTakenRequest,
    FuelGatheredRequest,
    ItemDroppedRequest,
    ItemThrownRequest,
    DarknessFearRequest,
    PowerRestoredRequest,
    FireLitRequest,
    FireAttemptRequest,
    LightSwitchUsedRequest,
    FireplaceUsedRequest,
)
