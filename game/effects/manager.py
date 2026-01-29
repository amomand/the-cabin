"""Effect manager for applying state changes."""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, Any, List

if TYPE_CHECKING:
    from game.player import Player
    from game.room import Room


class EffectManager:
    """
    Manages application of effects to game state.
    
    Handles fear/health deltas with clamping and inventory changes.
    """
    
    # Effect limits
    MAX_FEAR_DELTA = 2
    MIN_FEAR_DELTA = -2
    MAX_HEALTH_DELTA = 2
    MIN_HEALTH_DELTA = -2
    
    def apply_intent_effects(
        self,
        player: "Player",
        room: "Room",
        effects: Dict[str, Any],
        available_items: Dict[str, Any]
    ) -> None:
        """
        Apply effects from an AI intent.
        
        Args:
            player: The player to apply effects to
            room: The current room (for item transfers)
            effects: Effect dictionary from Intent
            available_items: Dict of item names to items in the game
        """
        if not effects:
            return
        
        # Apply fear delta with clamping
        fear_delta = int(effects.get("fear", 0))
        fear_delta = max(self.MIN_FEAR_DELTA, min(self.MAX_FEAR_DELTA, fear_delta))
        self.apply_fear_change(player, fear_delta)
        
        # Apply health delta with clamping
        health_delta = int(effects.get("health", 0))
        health_delta = max(self.MIN_HEALTH_DELTA, min(self.MAX_HEALTH_DELTA, health_delta))
        self.apply_health_change(player, health_delta)
        
        # Handle inventory removals
        inventory_remove = [str(x) for x in effects.get("inventory_remove", [])]
        for item_name in inventory_remove:
            player.remove_item(item_name)
        
        # Handle inventory additions (only from room items)
        inventory_add = [str(x) for x in effects.get("inventory_add", [])]
        for item_name in inventory_add:
            if item_name in available_items and room.has_item(item_name):
                item = room.remove_item(item_name)
                if item and item.is_carryable():
                    player.add_item(item)
    
    def apply_fear_change(self, player: "Player", delta: int) -> None:
        """
        Apply a fear change to the player.
        
        Args:
            player: The player
            delta: Fear delta (positive increases fear)
        """
        player.fear = max(0, min(100, player.fear + delta))
    
    def apply_health_change(self, player: "Player", delta: int) -> None:
        """
        Apply a health change to the player.
        
        Args:
            player: The player
            delta: Health delta (negative is damage)
        """
        player.health = max(0, min(100, player.health + delta))
    
    def apply_damage(self, player: "Player", damage: int, fear_increase: int = 0) -> None:
        """
        Apply damage and fear from combat/events.
        
        Args:
            player: The player
            damage: Health points to remove
            fear_increase: Fear points to add
        """
        player.health = max(0, player.health - damage)
        player.fear = min(100, player.fear + fear_increase)
