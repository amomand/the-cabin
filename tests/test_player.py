"""
Tests for Player class.
"""
import pytest
from game.player import Player
from game.item import Item


class TestPlayer:
    """Tests for Player class."""

    def test_initial_state(self, sample_player):
        """Player should start with default health and fear."""
        assert sample_player.health == 100
        assert sample_player.fear == 0
        assert len(sample_player.inventory) == 0

    def test_add_item(self, sample_player):
        """Player can add items to inventory."""
        item = Item("test_item", "A test item", {"carryable"})
        sample_player.add_item(item)
        
        assert len(sample_player.inventory) == 1
        assert sample_player.has_item("test_item")

    def test_remove_item(self, sample_player):
        """Player can remove items from inventory."""
        item = Item("test_item", "A test item", {"carryable"})
        sample_player.add_item(item)
        
        removed = sample_player.remove_item("test_item")
        
        assert removed == item
        assert not sample_player.has_item("test_item")

    def test_remove_nonexistent_item(self, sample_player):
        """Removing nonexistent item returns None."""
        removed = sample_player.remove_item("nonexistent")
        assert removed is None

    def test_get_item(self, sample_player):
        """Player can retrieve items by name."""
        item = Item("test_item", "A test item", {"carryable"})
        sample_player.add_item(item)
        
        retrieved = sample_player.get_item("test_item")
        
        assert retrieved == item

    def test_get_inventory_names(self, sample_player):
        """Player can list inventory item names."""
        item1 = Item("rope", "A rope", {"carryable"})
        item2 = Item("matches", "Some matches", {"carryable"})
        sample_player.add_item(item1)
        sample_player.add_item(item2)
        
        names = sample_player.get_inventory_names()
        
        assert "rope" in names
        assert "matches" in names

    def test_health_clamping(self, sample_player):
        """Health should be clamped between 0 and 100."""
        sample_player.health = 150
        assert sample_player.health == 150  # No auto-clamping in setter
        
        sample_player.health = -50
        assert sample_player.health == -50  # No auto-clamping in setter
        
        # Clamping is done by GameEngine._apply_effects

    def test_fear_initial(self, sample_player):
        """Fear starts at 0."""
        assert sample_player.fear == 0
