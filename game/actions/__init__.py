"""Action classes for The Cabin game engine."""

from game.actions.base import Action, ActionResult, ActionContext
from game.actions.registry import ActionRegistry
from game.actions.move import MoveAction
from game.actions.observe import LookAction, ListenAction
from game.actions.inventory import TakeAction, DropAction, InventoryAction
from game.actions.throw import ThrowAction
from game.actions.use import UseAction, UseCircuitBreakerAction, TurnOnLightsAction
from game.actions.light import LightAction
from game.actions.help import HelpAction, NoneAction

__all__ = [
    "Action", "ActionResult", "ActionContext", "ActionRegistry",
    "MoveAction", "LookAction", "ListenAction",
    "TakeAction", "DropAction", "InventoryAction",
    "ThrowAction", "UseAction", "UseCircuitBreakerAction", "TurnOnLightsAction",
    "LightAction", "HelpAction", "NoneAction",
]


def create_default_registry() -> ActionRegistry:
    """Create and populate a registry with all standard actions."""
    registry = ActionRegistry()
    registry.register(MoveAction())
    registry.register(LookAction())
    registry.register(ListenAction())
    registry.register(TakeAction())
    registry.register(DropAction())
    registry.register(InventoryAction())
    registry.register(ThrowAction())
    registry.register(UseAction())
    registry.register(UseCircuitBreakerAction())
    registry.register(TurnOnLightsAction())
    registry.register(LightAction())
    registry.register(HelpAction())
    registry.register(NoneAction())
    return registry
