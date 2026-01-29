"""
Tests for Wildlife class and wildlife behavior.
"""
import pytest
from game.wildlife import Wildlife, create_wildlife


class TestWildlife:
    """Tests for Wildlife class."""

    def test_wildlife_creation(self):
        """Wildlife can be created with name, description, and traits."""
        wolf = Wildlife(
            name="wolf",
            description="A gray wolf",
            traits={"vicious", "territorial"},
            visual_description="A gray wolf watches you.",
            sound_description="You hear a low growl.",
        )
        
        assert wolf.name == "wolf"
        assert "gray wolf" in wolf.visual_description
        assert "growl" in wolf.sound_description
        assert wolf.has_trait("vicious")

    def test_has_trait(self):
        """has_trait checks for specific traits."""
        wolf = Wildlife("wolf", "A wolf", traits={"vicious", "territorial"})
        
        assert wolf.has_trait("vicious")
        assert wolf.has_trait("territorial")
        assert not wolf.has_trait("harmless")

    def test_is_vicious(self):
        """is_vicious returns True for vicious wildlife."""
        vicious = Wildlife("wolf", "A wolf", traits={"vicious"})
        docile = Wildlife("deer", "A deer", traits={"docile"})
        
        assert vicious.is_vicious()
        assert not docile.is_vicious()

    def test_is_elusive(self):
        """is_elusive returns True for elusive (hidden) wildlife."""
        visible = Wildlife("deer", "A deer", traits={"docile"})
        hidden = Wildlife("snake", "A snake", traits={"elusive", "vicious"})
        
        assert not visible.is_elusive()
        assert hidden.is_elusive()

    def test_provoke_vicious_attacks(self):
        """Vicious wildlife attacks when provoked."""
        wolf = Wildlife("wolf", "A wolf", traits={"vicious"})
        
        result = wolf.provoke()
        
        assert result["action"] == "attack"
        assert result["health_damage"] > 0
        assert result["fear_increase"] > 0
        assert wolf.has_attacked

    def test_provoke_skittish_flees(self):
        """Skittish wildlife flees when provoked."""
        deer = Wildlife("deer", "A deer", traits={"skittish"})
        
        result = deer.provoke()
        
        assert result["action"] == "flee"
        assert result["remove_from_room"] is True

    def test_provoke_only_once(self):
        """Vicious wildlife only attacks once."""
        wolf = Wildlife("wolf", "A wolf", traits={"vicious"})
        
        # First provocation
        result1 = wolf.provoke()
        assert result1["action"] == "attack"
        
        # Second provocation - should not attack again
        result2 = wolf.provoke()
        assert result2["action"] != "attack"

    def test_str_representation(self):
        """Wildlife string representation is its name."""
        wolf = Wildlife("wolf", "A wolf", traits=set())
        assert str(wolf) == "wolf"


class TestCreateWildlife:
    """Tests for create_wildlife factory function."""

    def test_creates_wildlife_dict(self, sample_wildlife):
        """create_wildlife returns a dictionary of wildlife."""
        assert isinstance(sample_wildlife, dict)
        assert len(sample_wildlife) > 0

    def test_all_wildlife_have_descriptions(self, sample_wildlife):
        """All wildlife should have visual descriptions."""
        for animal in sample_wildlife.values():
            assert len(animal.visual_description) > 0
