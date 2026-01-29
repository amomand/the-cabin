"""
Tests for Item class and item creation.
"""
import pytest
from game.item import Item, create_items


class TestItem:
    """Tests for Item class."""

    def test_item_creation(self):
        """Item can be created with name, description, and traits."""
        item = Item("rope", "A sturdy rope", {"carryable", "throwable"})
        
        assert item.name == "rope"
        assert item.description == "A sturdy rope"
        assert "carryable" in item.traits
        assert "throwable" in item.traits

    def test_has_trait(self):
        """has_trait checks for specific traits."""
        item = Item("rope", "A rope", {"carryable", "usable"})
        
        assert item.has_trait("carryable")
        assert item.has_trait("usable")
        assert not item.has_trait("weapon")

    def test_is_carryable(self):
        """is_carryable returns True for carryable items."""
        carryable = Item("rope", "A rope", {"carryable"})
        fixed = Item("door", "A door", {"usable"})
        
        assert carryable.is_carryable()
        assert not fixed.is_carryable()

    def test_is_throwable(self):
        """is_throwable returns True for throwable items."""
        throwable = Item("stone", "A stone", {"throwable"})
        heavy = Item("anvil", "An anvil", {"carryable"})
        
        assert throwable.is_throwable()
        assert not heavy.is_throwable()

    def test_is_usable(self):
        """is_usable returns True for usable items."""
        usable = Item("matches", "Matches", {"usable"})
        inert = Item("rock", "A rock", set())
        
        assert usable.is_usable()
        assert not inert.is_usable()

    def test_is_weapon(self):
        """is_weapon returns True for weapon items."""
        weapon = Item("knife", "A knife", {"weapon"})
        harmless = Item("flower", "A flower", set())
        
        assert weapon.is_weapon()
        assert not harmless.is_weapon()

    def test_is_flammable(self):
        """is_flammable returns True for flammable items."""
        flammable = Item("paper", "Paper", {"flammable"})
        fireproof = Item("stone", "A stone", set())
        
        assert flammable.is_flammable()
        assert not fireproof.is_flammable()

    def test_str_representation(self):
        """Item string representation is its name."""
        item = Item("rope", "A rope", set())
        assert str(item) == "rope"

    def test_repr(self):
        """Item has useful repr."""
        item = Item("rope", "A rope", {"carryable"})
        repr_str = repr(item)
        
        assert "rope" in repr_str
        assert "carryable" in repr_str


class TestCreateItems:
    """Tests for create_items factory function."""

    def test_creates_items_dict(self, sample_items):
        """create_items returns a dictionary of items."""
        assert isinstance(sample_items, dict)
        assert len(sample_items) > 0

    def test_rope_exists(self, sample_items):
        """Rope item should exist with expected traits."""
        assert "rope" in sample_items
        rope = sample_items["rope"]
        assert rope.is_carryable()
        assert rope.is_throwable()

    def test_matches_exists(self, sample_items):
        """Matches item should exist with expected traits."""
        assert "matches" in sample_items
        matches = sample_items["matches"]
        assert matches.is_carryable()
        assert matches.is_usable()

    def test_all_items_have_names(self, sample_items):
        """All items should have non-empty names."""
        for item in sample_items.values():
            assert len(item.name) > 0

    def test_all_items_have_descriptions(self, sample_items):
        """All items should have non-empty descriptions."""
        for item in sample_items.values():
            assert len(item.description) > 0
