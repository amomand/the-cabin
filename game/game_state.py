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
                "current_room_been_here_before": self.map.current_room_been_here_before,
                # Per-room item placement, so taken/dropped items survive a load
                # instead of snapping back to the fresh Map's defaults.
                "room_items": {
                    room.id: [item.name for item in room.items]
                    for location in self.map.locations.values()
                    for room in location.rooms.values()
                },
            },
            "world_state": self.map.world_state.to_dict(),
            "quests": {
                "active_quest_id": (
                    self.quest_manager.active_quest.quest_id
                    if self.quest_manager.active_quest else None
                ),
                "completed_quests": list(self.quest_manager.completed_quests),
                # Update history keeps the held-thought view intact after a load.
                "updates": {
                    quest_id: [
                        {
                            "event_name": update.event_name,
                            "text": update.text,
                            "timestamp": update.timestamp,
                        }
                        for update in quest.updates
                    ]
                    for quest_id, quest in self.quest_manager.quests.items()
                    if quest.updates
                },
            },
            "cutscenes": {
                "played_ids": self.cutscene_manager.get_played_ids(),
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
        
        # Item lookup for restores. Saves store display names (item.name),
        # which can differ from the map.items dict key (e.g. key
        # "circuit_breaker" vs name "circuit breaker"), so resolve by name
        # first with the dict key as a fallback.
        items_by_name = {item.name: item for item in map.items.values()}

        def _resolve_item(name: str):
            return items_by_name.get(name) or map.items.get(name)

        # Restore inventory (requires item lookup)
        inventory_names = player_data.get("inventory", [])
        player.inventory.clear()
        for item_name in inventory_names:
            item = _resolve_item(item_name)
            if item is not None:
                player.add_item(item)

        # Restore per-room item placement. The map passed in is freshly built
        # with default placements, so without this a taken item exists in both
        # its original room and the restored inventory.
        map_data_items = data.get("map", {}).get("room_items")
        for location in map.locations.values():
            for room in location.rooms.values():
                if map_data_items is not None:
                    if room.id in map_data_items:
                        room.items = [
                            item
                            for item in (
                                _resolve_item(name) for name in map_data_items[room.id]
                            )
                            if item is not None
                        ]
                    # Rooms missing from the save keep their defaults: a room
                    # added after the save was written should not load empty.
                else:
                    # Legacy save without placement data: strip restored
                    # inventory items from their default rooms so they are
                    # not duplicated. Dropped items cannot be recovered.
                    room.items = [
                        item for item in room.items if item.name not in inventory_names
                    ]
        
        # Restore map state
        map_data = data.get("map", {})
        visited = set(map_data.get("visited_rooms", []))
        current_room_id = map_data.get("current_room_id")
        if current_room_id:
            visited.add(current_room_id)
        map.visited_rooms = visited
        
        # Navigate to saved room
        if current_room_id:
            map._set_current_room_by_id(
                current_room_id,
                been_here_before=map_data.get("current_room_been_here_before", False),
            )
        
        # Restore world state
        world_data = data.get("world_state", {})
        map.world_state = WorldState.from_dict(world_data)
        
        # Restore quest state
        from game.quest import QuestStatus

        quest_data = data.get("quests", {})
        # Normalise defensively: drop unknown quest IDs, and if a malformed
        # save lists the active quest as completed too, completed wins (it
        # cannot replay its opening that way).
        completed = [
            quest_id
            for quest_id in quest_data.get("completed_quests", [])
            if quest_id in quest_manager.quests
        ]
        quest_manager.completed_quests = list(completed)

        active_id = quest_data.get("active_quest_id")
        if active_id in completed or active_id not in quest_manager.quests:
            active_id = None
        quest_manager.active_quest = (
            quest_manager.quests[active_id] if active_id else None
        )

        # Restore each quest's status authoritatively. Every trigger, update,
        # and completion path gates on status, so without this a loaded active
        # quest stays INACTIVE (never updates or completes) and a completed
        # quest can re-trigger and replay its opening.
        saved_updates = quest_data.get("updates", {})
        for quest_id, quest in quest_manager.quests.items():
            if quest_id == active_id:
                quest.status = QuestStatus.ACTIVE
            elif quest_id in completed:
                quest.status = QuestStatus.COMPLETED
            else:
                quest.status = QuestStatus.INACTIVE
            quest.updates = []
            for update in saved_updates.get(quest_id, []):
                quest.add_update(
                    update.get("event_name", ""),
                    update.get("text", ""),
                    update.get("timestamp", 0.0),
                )

        # Restore cutscene play state so authored beats do not re-fire on load.
        cutscene_data = data.get("cutscenes", {})
        cutscene_manager.set_played_ids(cutscene_data.get("played_ids", []))

        return cls(
            player=player,
            map=map,
            quest_manager=quest_manager,
            cutscene_manager=cutscene_manager,
        )
