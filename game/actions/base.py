"""Base classes for game actions."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Iterable, Optional, TYPE_CHECKING

from game.events.requests import TURN_REQUEST_TYPES, TurnRequest

if TYPE_CHECKING:
    from game.player import Player
    from game.map import Map
    from game.ai_interpreter import Intent


class ModelEffectsPolicy(Enum):
    """Whether model-proposed effects may follow an action result."""

    APPLY = "apply"
    BLOCK = "block"


@dataclass(frozen=True)
class ActionResult:
    """Result of executing an action.

    Authored story results block model-proposed effects so their narration and
    deterministic state transitions remain the complete outcome of the beat.
    """
    
    success: bool
    feedback: str
    requests: tuple[TurnRequest, ...] = field(default_factory=tuple)
    model_effects: ModelEffectsPolicy = ModelEffectsPolicy.APPLY

    def __post_init__(self) -> None:
        """Freeze and validate the action-to-turn protocol at runtime."""
        raw_requests = self.requests
        if isinstance(raw_requests, (str, bytes)):
            raise TypeError(
                f"Unsupported turn request type: {type(raw_requests).__name__}"
            )
        try:
            frozen_requests = tuple(raw_requests)
        except TypeError as exc:
            raise TypeError(
                f"Unsupported turn request container: {type(raw_requests).__name__}"
            ) from exc

        unsupported = [
            request
            for request in frozen_requests
            if not isinstance(request, TURN_REQUEST_TYPES)
        ]
        if unsupported:
            names = ", ".join(type(request).__name__ for request in unsupported)
            raise TypeError(f"Unsupported turn request type: {names}")
        object.__setattr__(self, "requests", frozen_requests)
    
    @classmethod
    def success_result(
        cls,
        feedback: str,
        requests: Optional[Iterable[TurnRequest]] = None,
    ) -> "ActionResult":
        """Create a successful action result."""
        return cls(
            success=True,
            feedback=feedback,
            requests=() if requests is None else requests,
        )
    
    @classmethod
    def failure_result(cls, feedback: str) -> "ActionResult":
        """Create a failed action result."""
        return cls(success=False, feedback=feedback)

    @classmethod
    def authored(
        cls,
        feedback: str,
        *,
        success: bool = True,
        requests: Optional[Iterable[TurnRequest]] = None,
    ) -> "ActionResult":
        """Create an authored result that owns the turn's complete effects."""
        return cls(
            success=success,
            feedback=feedback,
            requests=() if requests is None else requests,
            model_effects=ModelEffectsPolicy.BLOCK,
        )


@dataclass
class ActionContext:
    """Context passed to actions for execution."""
    
    player: "Player"
    map: "Map"
    intent: "Intent"
    
    @property
    def room(self):
        """Get the current room."""
        return self.map.current_room
    
    @property
    def world_state(self):
        """Get the world state."""
        return self.map.world_state
    
    @property
    def args(self) -> Dict[str, str]:
        """Get intent arguments."""
        return self.intent.args or {}
    
    @property
    def ai_reply(self) -> Optional[str]:
        """Get the AI's suggested reply, if any."""
        return self.intent.reply


class Action(ABC):
    """Abstract base class for all game actions."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """The action name (matches intent.action)."""
        pass
    
    @abstractmethod
    def execute(self, ctx: ActionContext) -> ActionResult:
        """
        Execute the action.
        
        Args:
            ctx: The action context containing player, map, and intent.
            
        Returns:
            ActionResult with success status, feedback, and ordered turn requests.
        """
        pass
