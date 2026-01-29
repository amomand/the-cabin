"""Action registry for dispatching actions by name."""

from __future__ import annotations

from typing import Dict, Optional, TYPE_CHECKING

from game.actions.base import Action, ActionContext, ActionResult

if TYPE_CHECKING:
    from game.player import Player
    from game.map import Map
    from game.ai_interpreter import Intent


class ActionRegistry:
    """Registry that maps action names to Action instances."""
    
    def __init__(self) -> None:
        self._actions: Dict[str, Action] = {}
    
    def register(self, action: Action) -> None:
        """Register an action by its name."""
        self._actions[action.name] = action
    
    def get(self, name: str) -> Optional[Action]:
        """Get an action by name, or None if not found."""
        return self._actions.get(name)
    
    def has(self, name: str) -> bool:
        """Check if an action is registered."""
        return name in self._actions
    
    def execute(
        self,
        action_name: str,
        player: "Player",
        map: "Map",
        intent: "Intent"
    ) -> Optional[ActionResult]:
        """
        Execute an action by name.
        
        Args:
            action_name: The name of the action to execute.
            player: The player instance.
            map: The map instance.
            intent: The parsed intent from the AI interpreter.
            
        Returns:
            ActionResult if the action was found and executed, None otherwise.
        """
        action = self.get(action_name)
        if action is None:
            return None
        
        ctx = ActionContext(player=player, map=map, intent=intent)
        return action.execute(ctx)
    
    @property
    def registered_actions(self) -> list[str]:
        """Get list of registered action names."""
        return list(self._actions.keys())
