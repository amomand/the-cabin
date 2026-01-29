"""Tests for EffectManager."""

import pytest
from unittest.mock import MagicMock

from game.effects.manager import EffectManager


class TestEffectManager:
    """Tests for EffectManager."""
    
    @pytest.fixture
    def manager(self):
        return EffectManager()
    
    @pytest.fixture
    def mock_player(self):
        player = MagicMock()
        player.health = 100
        player.fear = 0
        return player
    
    def test_apply_fear_change_increase(self, manager, mock_player):
        """Fear can be increased."""
        manager.apply_fear_change(mock_player, 10)
        
        assert mock_player.fear == 10
    
    def test_apply_fear_change_decrease(self, manager, mock_player):
        """Fear can be decreased."""
        mock_player.fear = 50
        
        manager.apply_fear_change(mock_player, -10)
        
        assert mock_player.fear == 40
    
    def test_apply_fear_clamped_at_zero(self, manager, mock_player):
        """Fear doesn't go below zero."""
        mock_player.fear = 5
        
        manager.apply_fear_change(mock_player, -20)
        
        assert mock_player.fear == 0
    
    def test_apply_fear_clamped_at_100(self, manager, mock_player):
        """Fear doesn't go above 100."""
        mock_player.fear = 95
        
        manager.apply_fear_change(mock_player, 20)
        
        assert mock_player.fear == 100
    
    def test_apply_health_change_increase(self, manager, mock_player):
        """Health can be increased."""
        mock_player.health = 80
        
        manager.apply_health_change(mock_player, 10)
        
        assert mock_player.health == 90
    
    def test_apply_health_change_decrease(self, manager, mock_player):
        """Health can be decreased."""
        manager.apply_health_change(mock_player, -10)
        
        assert mock_player.health == 90
    
    def test_apply_health_clamped_at_zero(self, manager, mock_player):
        """Health doesn't go below zero."""
        mock_player.health = 5
        
        manager.apply_health_change(mock_player, -20)
        
        assert mock_player.health == 0
    
    def test_apply_health_clamped_at_100(self, manager, mock_player):
        """Health doesn't go above 100."""
        manager.apply_health_change(mock_player, 20)
        
        assert mock_player.health == 100
    
    def test_apply_damage(self, manager, mock_player):
        """apply_damage reduces health and increases fear."""
        manager.apply_damage(mock_player, damage=15, fear_increase=10)
        
        assert mock_player.health == 85
        assert mock_player.fear == 10
    
    def test_apply_intent_effects_with_clamping(self, manager, mock_player):
        """Intent effects are clamped to limits."""
        room = MagicMock()
        
        effects = {
            "fear": 10,  # Should be clamped to 2
            "health": -10  # Should be clamped to -2
        }
        
        manager.apply_intent_effects(mock_player, room, effects, {})
        
        assert mock_player.fear == 2  # Clamped from 10
        assert mock_player.health == 98  # Clamped from -10
    
    def test_apply_intent_effects_inventory_remove(self, manager, mock_player):
        """Inventory items can be removed via effects."""
        room = MagicMock()
        
        effects = {
            "inventory_remove": ["rope"]
        }
        
        manager.apply_intent_effects(mock_player, room, effects, {})
        
        mock_player.remove_item.assert_called_with("rope")
    
    def test_apply_intent_effects_empty(self, manager, mock_player):
        """Empty effects dict is handled."""
        room = MagicMock()
        
        manager.apply_intent_effects(mock_player, room, {}, {})
        
        # Should not raise
        assert mock_player.health == 100
