"""Cutscene event listener - triggers cutscenes on room transitions."""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from game.events.types import PlayerMovedEvent

if TYPE_CHECKING:
    from game.player import Player
    from game.world_state import WorldState
    from game.cutscene import CutsceneManager


class CutsceneEventListener:
    """
    Listens for player movement and triggers cutscenes.
    
    Replaces manual cutscene checks in GameEngine movement handling.
    """
    
    def __init__(
        self,
        cutscene_manager: "CutsceneManager",
        get_player: Callable[[], "Player"],
        get_world_state: Callable[[], "WorldState"],
    ):
        """
        Initialize the cutscene listener.
        
        Args:
            cutscene_manager: The cutscene manager instance
            get_player: Callable to get current player state
            get_world_state: Callable to get current world state
        """
        self.cutscene_manager = cutscene_manager
        self.get_player = get_player
        self.get_world_state = get_world_state
    
    def register(self, event_bus) -> None:
        """Register event handlers with the event bus."""
        event_bus.subscribe("PlayerMovedEvent", self._on_player_moved)
    
    def _on_player_moved(self, event: PlayerMovedEvent) -> None:
        """Handle player movement - check for cutscene triggers."""
        player = self.get_player()
        world_state = self.get_world_state()
        
        self.cutscene_manager.check_and_play_cutscenes(
            from_room_id=event.from_room_id,
            to_room_id=event.to_room_id,
            player=player,
            world_state=world_state
        )
