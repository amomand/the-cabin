"""Tests for ActionRegistry."""

import pytest
from unittest.mock import MagicMock

from game.actions.base import Action, ActionContext, ActionResult
from game.actions.registry import ActionRegistry


class MockAction(Action):
    """A mock action for testing."""
    
    def __init__(self, action_name: str = "mock"):
        self._name = action_name
    
    @property
    def name(self) -> str:
        return self._name
    
    def execute(self, ctx: ActionContext) -> ActionResult:
        return ActionResult.success_result(f"Executed {self._name}")


class TestActionRegistry:
    """Tests for ActionRegistry."""
    
    def test_register_and_get(self):
        """Can register and retrieve an action."""
        registry = ActionRegistry()
        action = MockAction("test_action")
        
        registry.register(action)
        
        retrieved = registry.get("test_action")
        assert retrieved is action
    
    def test_get_unregistered_returns_none(self):
        """Getting an unregistered action returns None."""
        registry = ActionRegistry()
        
        result = registry.get("nonexistent")
        
        assert result is None
    
    def test_has_registered_action(self):
        """has() returns True for registered actions."""
        registry = ActionRegistry()
        registry.register(MockAction("exists"))
        
        assert registry.has("exists") is True
        assert registry.has("not_exists") is False
    
    def test_execute_registered_action(self):
        """Can execute a registered action."""
        registry = ActionRegistry()
        registry.register(MockAction("move"))
        
        # Create mock objects
        player = MagicMock()
        map_mock = MagicMock()
        intent = MagicMock()
        intent.args = {}
        intent.reply = None
        
        result = registry.execute("move", player, map_mock, intent)
        
        assert result is not None
        assert result.success is True
        assert result.feedback == "Executed move"
    
    def test_execute_unregistered_returns_none(self):
        """Executing an unregistered action returns None."""
        registry = ActionRegistry()
        
        player = MagicMock()
        map_mock = MagicMock()
        intent = MagicMock()
        
        result = registry.execute("nonexistent", player, map_mock, intent)
        
        assert result is None
    
    def test_registered_actions_list(self):
        """Can get list of registered action names."""
        registry = ActionRegistry()
        registry.register(MockAction("move"))
        registry.register(MockAction("look"))
        registry.register(MockAction("take"))
        
        actions = registry.registered_actions
        
        assert set(actions) == {"move", "look", "take"}
    
    def test_register_overwrites_existing(self):
        """Registering an action with the same name overwrites the previous."""
        registry = ActionRegistry()
        action1 = MockAction("test")
        action2 = MockAction("test")
        
        registry.register(action1)
        registry.register(action2)
        
        assert registry.get("test") is action2
