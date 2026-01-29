"""
Unified game state container for The Cabin.

This provides a single object that holds all game state,
making it easy to pass around, serialize, and test.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, TYPE_CHECKING

if TYPE_CHECKING:
    from game.player import Player
    from game.map import Map
    from game.quest import QuestManager
    from game.cutscene import CutsceneManager
    from game.world_state import WorldState


@dataclass
class GameState:
    """
    Unified container for all game state.
    
    This is the single source of truth passed to actions,
    events, and other systems that need access to game state.
    """
    
    player: 'Player'
    map: 'Map'
    quest_manager: 'QuestManager'
    cutscene_manager: 'CutsceneManager'
    
    # Transient state (not saved)
    last_feedback: str = ""
    is_running: bool = True
    
    @property
    def current_room(self):
        """Convenience accessor for current room."""
        return self.map.current_room
    
    @property
    def world_state(self) -> 'WorldState':
        """Convenience accessor for world state."""
        return self.map.world_state
    
    @property
    def visited_rooms(self) -> set:
        """Convenience accessor for visited rooms."""
        return self.map.visited_rooms
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for serialization (save game).
        
        Only includes persistable state, not transient fields.
        """
        return {
            "player": {
                "health": self.player.health,
                "fear": self.player.fear,
                "inventory": [item.name for item in self.player.inventory],
            },
            "map": {
                "current_room_id": self.map.current_room.id,
                "visited_rooms": list(self.map.visited_rooms),
            },
            "world_state": self.map.world_state.to_dict(),
            "quests": {
                "active_quest_id": (
                    self.quest_manager.active_quest.quest_id 
                    if self.quest_manager.active_quest else None
                ),
                "completed_quests": list(self.quest_manager.completed_quests),
            },
            "cutscenes": {
                "played_ids": [
                    cs.text[:50] for cs in self.cutscene_manager.cutscenes 
                    if cs.has_played
                ],
            },
        }
    
    @classmethod
    def from_dict(
        cls,
        data: Dict[str, Any],
        player: 'Player',
        map: 'Map',
        quest_manager: 'QuestManager',
        cutscene_manager: 'CutsceneManager',
    ) -> 'GameState':
        """
        Restore state from dictionary (load game).
        
        Requires fresh instances of the main objects which are then
        populated with the saved state.
        """
        from game.world_state import WorldState
        
        # Restore player state
        player_data = data.get("player", {})
        player.health = player_data.get("health", 100)
        player.fear = player_data.get("fear", 0)
        
        # Restore inventory (requires item lookup)
        inventory_names = player_data.get("inventory", [])
        player.inventory.clear()
        for item_name in inventory_names:
            if item_name in map.items:
                player.add_item(map.items[item_name])
        
        # Restore map state
        map_data = data.get("map", {})
        visited = set(map_data.get("visited_rooms", []))
        map.visited_rooms = visited
        
        # Navigate to saved room
        current_room_id = map_data.get("current_room_id")
        if current_room_id:
            map._set_current_room_by_id(current_room_id)
        
        # Restore world state
        world_data = data.get("world_state", {})
        map.world_state = WorldState.from_dict(world_data)
        
        # Restore quest state
        quest_data = data.get("quests", {})
        completed = quest_data.get("completed_quests", [])
        quest_manager.completed_quests = list(completed)
        
        active_id = quest_data.get("active_quest_id")
        if active_id and active_id in quest_manager.quests:
            quest_manager.active_quest = quest_manager.quests[active_id]
        
        return cls(
            player=player,
            map=map,
            quest_manager=quest_manager,
            cutscene_manager=cutscene_manager,
        )
