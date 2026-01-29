"""Tests for RenderManager and TerminalAdapter."""

import pytest
from unittest.mock import MagicMock, patch

from game.render.terminal import TerminalAdapter
from game.render.manager import RenderManager


class TestTerminalAdapter:
    """Tests for TerminalAdapter."""
    
    def test_clear_screen_unix(self):
        """clear_screen calls os.system with 'clear' on Unix."""
        adapter = TerminalAdapter()
        
        with patch("os.name", "posix"), patch("os.system") as mock_system:
            adapter.clear_screen()
            mock_system.assert_called_once_with("clear")
    
    def test_clear_screen_windows(self):
        """clear_screen calls os.system with 'cls' on Windows."""
        adapter = TerminalAdapter()
        
        with patch("os.name", "nt"), patch("os.system") as mock_system:
            adapter.clear_screen()
            mock_system.assert_called_once_with("cls")
    
    def test_print(self, capsys):
        """print outputs text."""
        adapter = TerminalAdapter()
        
        adapter.print("Hello, world!")
        
        captured = capsys.readouterr()
        assert "Hello, world!" in captured.out
    
    def test_print_line(self, capsys):
        """print_line outputs a line."""
        adapter = TerminalAdapter()
        
        adapter.print_line("Test line")
        
        captured = capsys.readouterr()
        assert "Test line\n" in captured.out
    
    def test_print_blank_line(self, capsys):
        """print_blank_line outputs a blank line."""
        adapter = TerminalAdapter()
        
        adapter.print_blank_line()
        
        captured = capsys.readouterr()
        assert captured.out == "\n"


class TestRenderManager:
    """Tests for RenderManager."""
    
    @pytest.fixture
    def mock_terminal(self):
        return MagicMock(spec=TerminalAdapter)
    
    @pytest.fixture
    def render_manager(self, mock_terminal):
        return RenderManager(terminal=mock_terminal)
    
    @pytest.fixture
    def mock_room(self):
        room = MagicMock()
        room.id = "test_room"
        room.name = "Test Room"
        room.get_description.return_value = "A test room description."
        return room
    
    @pytest.fixture
    def mock_player(self):
        player = MagicMock()
        player.health = 100
        player.fear = 0
        return player
    
    @pytest.fixture
    def mock_world_state(self):
        return MagicMock()
    
    def test_render_intro(self, render_manager, mock_terminal):
        """render_intro displays intro text and waits for keypress."""
        render_manager.render_intro()
        
        mock_terminal.clear_screen.assert_called_once()
        assert mock_terminal.print_line.call_count >= 3  # 3 intro lines
        mock_terminal.wait_for_keypress.assert_called_once()
    
    def test_render_room_first_time(self, render_manager, mock_terminal, mock_room, mock_player, mock_world_state):
        """First render clears screen and shows room."""
        render_manager.render_room(mock_room, mock_player, mock_world_state)
        
        mock_terminal.clear_screen.assert_called_once()
        # Check room name was printed
        calls = [str(call) for call in mock_terminal.print_line.call_args_list]
        assert any("Test Room" in str(c) for c in calls)
    
    def test_render_room_same_room_no_clear(self, render_manager, mock_terminal, mock_room, mock_player, mock_world_state):
        """Rendering same room doesn't clear screen again."""
        render_manager.render_room(mock_room, mock_player, mock_world_state)
        mock_terminal.reset_mock()
        
        render_manager.render_room(mock_room, mock_player, mock_world_state)
        
        mock_terminal.clear_screen.assert_not_called()
    
    def test_render_room_with_feedback(self, render_manager, mock_terminal, mock_room, mock_player, mock_world_state):
        """Feedback is displayed when provided."""
        render_manager.render_room(mock_room, mock_player, mock_world_state, feedback="You found a key!")
        
        calls = [str(call) for call in mock_terminal.print_line.call_args_list]
        assert any("found a key" in str(c) for c in calls)
    
    def test_render_room_shows_status(self, render_manager, mock_terminal, mock_room, mock_player, mock_world_state):
        """Status bar shows health and fear."""
        render_manager.render_room(mock_room, mock_player, mock_world_state)
        
        calls = [str(call) for call in mock_terminal.print_line.call_args_list]
        assert any("Health: 100" in str(c) for c in calls)
        assert any("Fear: 0" in str(c) for c in calls)
    
    def test_render_quest_screen(self, render_manager, mock_terminal):
        """render_quest_screen displays quest text and waits."""
        render_manager.render_quest_screen("Find the cabin key.")
        
        mock_terminal.clear_screen.assert_called_once()
        calls = [str(call) for call in mock_terminal.print_line.call_args_list]
        assert any("cabin key" in str(c) for c in calls)
        mock_terminal.wait_for_keypress.assert_called_once()
    
    def test_force_room_redraw(self, render_manager, mock_terminal, mock_room, mock_player, mock_world_state):
        """force_room_redraw causes next render to clear screen."""
        render_manager.render_room(mock_room, mock_player, mock_world_state)
        mock_terminal.reset_mock()
        
        render_manager.force_room_redraw()
        render_manager.render_room(mock_room, mock_player, mock_world_state)
        
        mock_terminal.clear_screen.assert_called_once()
