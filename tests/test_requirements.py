"""
Tests for Requirements system.
"""
import pytest
from game.requirements import (
    Requirement,
    HasItem,
    WorldFlagTrue,
    FearBelow,
    CustomRequirement,
)
from game.player import Player
from game.item import Item


class TestHasItem:
    """Tests for HasItem requirement."""

    def test_met_when_player_has_item(self):
        """Requirement is met when player has the item."""
        player = Player()
        item = Item("key", "A key", {"carryable"})
        player.add_item(item)
        
        req = HasItem("key")
        
        assert req.is_met(player, {})

    def test_not_met_when_missing_item(self):
        """Requirement is not met when player lacks the item."""
        player = Player()
        
        req = HasItem("key")
        
        assert not req.is_met(player, {})

    def test_denial_text(self):
        """Denial text mentions the missing item."""
        player = Player()
        req = HasItem("key")
        
        denial = req.denial_text(player, {})
        
        assert len(denial) > 0


class TestWorldFlagTrue:
    """Tests for WorldFlagTrue requirement."""

    def test_met_when_flag_is_true(self):
        """Requirement is met when world flag is True."""
        world_state = {"has_power": True}
        
        req = WorldFlagTrue("has_power")
        
        assert req.is_met(None, world_state)

    def test_not_met_when_flag_is_false(self):
        """Requirement is not met when world flag is False."""
        world_state = {"has_power": False}
        
        req = WorldFlagTrue("has_power")
        
        assert not req.is_met(None, world_state)

    def test_not_met_when_flag_missing(self):
        """Requirement is not met when world flag doesn't exist."""
        world_state = {}
        
        req = WorldFlagTrue("has_power")
        
        assert not req.is_met(None, world_state)

    def test_works_with_world_state_object(self):
        """Requirement works with WorldState object (dict-style access)."""
        from game.world_state import WorldState
        
        world_state = WorldState(has_power=True)
        req = WorldFlagTrue("has_power")
        
        # WorldState supports .get() for backward compatibility
        assert req.is_met(None, world_state)


class TestFearBelow:
    """Tests for FearBelow requirement."""

    def test_met_when_fear_below_threshold(self):
        """Requirement is met when player fear is below threshold."""
        player = Player()
        player.fear = 30
        
        req = FearBelow(50)
        
        assert req.is_met(player, {})

    def test_not_met_when_fear_at_threshold(self):
        """Requirement is not met when fear equals threshold."""
        player = Player()
        player.fear = 50
        
        req = FearBelow(50)
        
        assert not req.is_met(player, {})

    def test_not_met_when_fear_above_threshold(self):
        """Requirement is not met when fear exceeds threshold."""
        player = Player()
        player.fear = 70
        
        req = FearBelow(50)
        
        assert not req.is_met(player, {})


class TestCustomRequirement:
    """Tests for CustomRequirement."""

    def test_custom_predicate(self):
        """CustomRequirement uses provided predicate."""
        player = Player()
        player.health = 80
        
        req = CustomRequirement(
            predicate=lambda p, ws: p.health > 50,
            message="You're too weak."
        )
        
        assert req.is_met(player, {})
        
        player.health = 30
        assert not req.is_met(player, {})

    def test_custom_denial_text(self):
        """CustomRequirement returns provided message."""
        req = CustomRequirement(
            predicate=lambda p, ws: False,
            message="Custom denial message."
        )
        
        assert req.denial_text(None, {}) == "Custom denial message."
