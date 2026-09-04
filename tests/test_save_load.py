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

    def test_dir_not_created_on_init(self, save_dir):
        """Constructing a SaveManager must not create the directory (lazy)."""
        assert not save_dir.exists()
        SaveManager(save_dir=save_dir)
        assert not save_dir.exists()

    def test_dir_created_lazily_on_first_save(self, manager, mock_game_state, save_dir):
        """The directory is created only when a save is actually written."""
        assert not save_dir.exists()
        manager.save_game(mock_game_state, "slot")
        assert save_dir.exists()
        assert (save_dir / "slot.json").exists()
    
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


@pytest.mark.parametrize("phone_location", ["inventory", "cabin_main", "cabin_grounds_main"])
def test_pre_evening_slots_migrate_equipment_without_losing_carried_items(tmp_path, monkeypatch, phone_location):
    from server.session import WebGameSession
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    session = WebGameSession()
    session.save_manager = SaveManager(tmp_path)
    for command in ("", "take stone", "north", "cabin", "", "", "take matches", "save legacy"):
        session.handle_input(command)
    path = tmp_path / "legacy.json"
    payload = json.loads(path.read_text())
    saved = payload["game_state"]
    for field in ("reopening_done", "evening_meal", "slept_cold", "morning_started"):
        saved["world_state"].pop(field)
    rooms = saved["map"]["room_items"]
    rooms["cabin_main"].remove("table")
    rooms["konttori"] = ["camera feed"]
    if phone_location == "inventory":
        saved["player"]["inventory"].append("phone")
    else:
        rooms[phone_location].append("phone")
    path.write_text(json.dumps(payload))
    session.handle_input("load legacy")
    assert set(session.player.get_inventory_names()) == {"stone", "matches"}
    for location in session.map.locations.values():
        for room in location.rooms.values():
            assert not {"phone", "camera feed", "stone", "matches"}.intersection(item.name for item in room.items)
    meal = session.handle_input("use table")
    assert "bread" in " ".join(meal.lines)
    assert session.map.world_state.reopening_done and session.map.world_state.evening_meal
    session.handle_input("north")
    monitor = session.handle_input("use monitor")
    assert "monitor is dark" in " ".join(monitor.lines)
    assert not session.map.world_state.footage_reviewed
