"""Tests for SaveManager."""

import pytest
import json
from pathlib import Path
from unittest.mock import MagicMock

from game.persistence.save_manager import SaveManager


class TestSaveManager:
    """Tests for SaveManager."""
    
    @pytest.fixture
    def save_dir(self, tmp_path):
        """Create a temporary save directory."""
        return tmp_path / "saves"
    
    @pytest.fixture
    def manager(self, save_dir):
        return SaveManager(save_dir=save_dir)
    
    @pytest.fixture
    def mock_game_state(self):
        state = MagicMock()
        state.to_dict.return_value = {
            "player": {"health": 100, "fear": 10},
            "map": {"current_room_id": "cabin"}
        }
        return state
    
    def test_save_creates_file(self, manager, mock_game_state, save_dir):
        """Saving creates a JSON file."""
        path = manager.save_game(mock_game_state, "test_save")
        
        assert path.exists()
        assert path.suffix == ".json"
    
    def test_save_contains_game_state(self, manager, mock_game_state, save_dir):
        """Saved file contains game state."""
        manager.save_game(mock_game_state, "test_save")
        
        save_path = save_dir / "test_save.json"
        with open(save_path) as f:
            data = json.load(f)
        
        assert "game_state" in data
        assert data["game_state"]["player"]["health"] == 100
    
    def test_save_contains_metadata(self, manager, mock_game_state, save_dir):
        """Saved file contains metadata."""
        manager.save_game(mock_game_state, "test_save")
        
        save_path = save_dir / "test_save.json"
        with open(save_path) as f:
            data = json.load(f)
        
        assert "version" in data
        assert "timestamp" in data
        assert data["slot_name"] == "test_save"
    
    def test_load_returns_game_state(self, manager, mock_game_state, save_dir):
        """Loading returns the game state dict."""
        manager.save_game(mock_game_state, "test_save")
        
        loaded = manager.load_game("test_save")
        
        assert loaded is not None
        assert loaded["player"]["health"] == 100
    
    def test_load_nonexistent_returns_none(self, manager):
        """Loading nonexistent save returns None."""
        loaded = manager.load_game("nonexistent")
        
        assert loaded is None
    
    def test_save_exists(self, manager, mock_game_state):
        """save_exists returns correct values."""
        assert manager.save_exists("test_save") is False
        
        manager.save_game(mock_game_state, "test_save")
        
        assert manager.save_exists("test_save") is True
    
    def test_delete_save(self, manager, mock_game_state, save_dir):
        """delete_save removes the save file."""
        manager.save_game(mock_game_state, "test_save")
        
        result = manager.delete_save("test_save")
        
        assert result is True
        assert not (save_dir / "test_save.json").exists()
    
    def test_delete_nonexistent_returns_false(self, manager):
        """delete_save returns False for nonexistent file."""
        result = manager.delete_save("nonexistent")
        
        assert result is False
    
    def test_list_saves(self, manager, mock_game_state):
        """list_saves returns all saves."""
        manager.save_game(mock_game_state, "save1")
        manager.save_game(mock_game_state, "save2")
        
        saves = manager.list_saves()
        
        assert len(saves) == 2
        slot_names = {s.slot_name for s in saves}
        assert "save1" in slot_names
        assert "save2" in slot_names
    
    def test_list_saves_empty(self, manager):
        """list_saves returns empty list when no saves."""
        saves = manager.list_saves()
        
        assert saves == []
    
    def test_sanitizes_slot_name(self, manager, mock_game_state, save_dir):
        """Slot names are sanitized."""
        manager.save_game(mock_game_state, "my/dangerous/../save")
        
        # Should create safe filename
        assert (save_dir / "mydangeroussave.json").exists()
    
    def test_default_slot_is_autosave(self, manager, mock_game_state, save_dir):
        """Default slot name is autosave."""
        manager.save_game(mock_game_state)
        
        assert (save_dir / "autosave.json").exists()
