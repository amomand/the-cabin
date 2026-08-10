"""Base classes for game actions."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from game.player import Player
    from game.map import Map
    from game.ai_interpreter import Intent


class ModelEffectsPolicy(Enum):
    """Whether model-proposed effects may follow an action result."""

    APPLY = "apply"
    BLOCK = "block"


@dataclass
class ActionResult:
    """Result of executing an action.

    Authored story results block model-proposed effects so their narration and
    deterministic state transitions remain the complete outcome of the beat.
    """
    
    success: bool
    feedback: str
    events: List[str] = field(default_factory=list)
    state_changes: Dict[str, Any] = field(default_factory=dict)
    model_effects: ModelEffectsPolicy = ModelEffectsPolicy.APPLY
    
    @classmethod
    def success_result(
        cls,
        feedback: str,
        events: Optional[List[str]] = None,
        state_changes: Optional[Dict[str, Any]] = None
    ) -> "ActionResult":
        """Create a successful action result."""
        return cls(
            success=True,
            feedback=feedback,
            events=events if events is not None else [],
            state_changes=state_changes if state_changes is not None else {},
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
        events: Optional[List[str]] = None,
        state_changes: Optional[Dict[str, Any]] = None,
    ) -> "ActionResult":
        """Create an authored result that owns the turn's complete effects."""
        return cls(
            success=success,
            feedback=feedback,
            events=events if events is not None else [],
            state_changes=state_changes if state_changes is not None else {},
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
            ActionResult with success status, feedback, and any events/state changes.
        """
        pass
