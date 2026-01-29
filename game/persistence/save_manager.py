"""Save/load functionality for The Cabin."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from game.game_state import GameState


@dataclass
class SaveInfo:
    """Information about a save file."""
    slot_name: str
    timestamp: str
    room_name: str
    player_health: int
    player_fear: int
    file_path: Path


class SaveManager:
    """
    Manages save and load operations.
    
    Saves are stored as JSON files in the saves directory.
    """
    
    SAVE_VERSION = 1
    
    def __init__(self, save_dir: Optional[Path] = None) -> None:
        """
        Initialize the save manager.
        
        Args:
            save_dir: Directory for save files. Defaults to ./saves/
        """
        self.save_dir = save_dir or Path("saves")
        self._ensure_save_dir()
    
    def _ensure_save_dir(self) -> None:
        """Create the save directory if it doesn't exist."""
        self.save_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_save_path(self, slot_name: str) -> Path:
        """Get the path for a save slot."""
        # Sanitize slot name
        safe_name = "".join(c for c in slot_name if c.isalnum() or c in "-_")
        if not safe_name:
            safe_name = "save"
        return self.save_dir / f"{safe_name}.json"
    
    def save_game(self, game_state: "GameState", slot_name: str = "autosave") -> Path:
        """
        Save the game to a slot.
        
        Args:
            game_state: The game state to save
            slot_name: Name of the save slot
            
        Returns:
            Path to the saved file
        """
        save_path = self._get_save_path(slot_name)
        
        save_data = {
            "version": self.SAVE_VERSION,
            "timestamp": datetime.now().isoformat(),
            "slot_name": slot_name,
            "game_state": game_state.to_dict()
        }
        
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(save_data, f, indent=2, ensure_ascii=False)
        
        return save_path
    
    def load_game(self, slot_name: str = "autosave") -> Optional[Dict[str, Any]]:
        """
        Load a game from a slot.
        
        Args:
            slot_name: Name of the save slot
            
        Returns:
            The saved game state dict, or None if not found
        """
        save_path = self._get_save_path(slot_name)
        
        if not save_path.exists():
            return None
        
        try:
            with open(save_path, "r", encoding="utf-8") as f:
                save_data = json.load(f)
            
            # Version check
            if save_data.get("version", 0) > self.SAVE_VERSION:
                return None  # Incompatible future version
            
            return save_data.get("game_state")
        except (json.JSONDecodeError, IOError):
            return None
    
    def list_saves(self) -> List[SaveInfo]:
        """
        List all available save files.
        
        Returns:
            List of SaveInfo objects for each save
        """
        saves = []
        
        for save_file in self.save_dir.glob("*.json"):
            try:
                with open(save_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                game_state = data.get("game_state", {})
                player = game_state.get("player", {})
                map_state = game_state.get("map", {})
                
                saves.append(SaveInfo(
                    slot_name=data.get("slot_name", save_file.stem),
                    timestamp=data.get("timestamp", "Unknown"),
                    room_name=map_state.get("current_room_id", "Unknown"),
                    player_health=player.get("health", 100),
                    player_fear=player.get("fear", 0),
                    file_path=save_file
                ))
            except (json.JSONDecodeError, IOError):
                continue
        
        # Sort by timestamp, newest first
        saves.sort(key=lambda s: s.timestamp, reverse=True)
        return saves
    
    def delete_save(self, slot_name: str) -> bool:
        """
        Delete a save file.
        
        Args:
            slot_name: Name of the save slot to delete
            
        Returns:
            True if deleted, False if not found
        """
        save_path = self._get_save_path(slot_name)
        
        if save_path.exists():
            save_path.unlink()
            return True
        return False
    
    def save_exists(self, slot_name: str) -> bool:
        """Check if a save slot exists."""
        return self._get_save_path(slot_name).exists()
