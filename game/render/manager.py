"""Render manager for game display."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from game.render.terminal import TerminalAdapter

if TYPE_CHECKING:
    from game.player import Player
    from game.map import Map
    from game.world_state import WorldState


class RenderManager:
    """
    Handles all game rendering/display logic.
    
    Extracted from GameEngine to separate concerns.
    """
    
    def __init__(self, terminal: Optional[TerminalAdapter] = None) -> None:
        self.terminal = terminal or TerminalAdapter()
        self._last_room_id: Optional[str] = None
        self._is_first_render: bool = True
    
    def clear_screen(self) -> None:
        """Clear the terminal screen."""
        self.terminal.clear_screen()
    
    def render_intro(self) -> None:
        """Display the intro sequence."""
        self.clear_screen()
        
        intro_lines = [
            "You shouldn't have come back.",
            "It's awake.",
            "It always has been."
        ]
        
        for line in intro_lines:
            self.terminal.print_line(line)
        
        self.terminal.print_blank_line()
        self.terminal.wait_for_keypress()
    
    def render_room(
        self,
        room,
        player: "Player",
        world_state: "WorldState",
        feedback: str = "",
        force: bool = False
    ) -> None:
        """
        Render the current room.
        
        Args:
            room: The current room
            player: The player instance
            world_state: The world state
            feedback: One-shot feedback message to display
            force: Force re-render even if room hasn't changed
        """
        room_changed = room.id != self._last_room_id or self._is_first_render or force
        
        if room_changed:
            self.clear_screen()
            self._last_room_id = room.id
            self._is_first_render = False
            
            # Room header
            self.terminal.print_line(room.name)
            self.terminal.print_line("-" * len(room.name))
            
            # Room description
            description = room.get_description(player, world_state)
            self.terminal.print_line(description)
            self.terminal.print_blank_line()
        
        # Feedback (one-shot)
        if feedback:
            self.terminal.print_line(feedback)
            self.terminal.print_blank_line()
        
        # Status bar
        self.terminal.print_line(f"Health: {player.health}    Fear: {player.fear}")
        self.terminal.print_blank_line()
        
        # Prompt
        self.terminal.print_line("What would you like to do?")
    
    def render_quest_screen(self, quest_text: str) -> None:
        """
        Render the quest screen.
        
        Args:
            quest_text: The quest text to display
        """
        self.clear_screen()
        
        self.terminal.print_line("*You take a breath and focus...*")
        self.terminal.print_blank_line()
        self.terminal.print_line(quest_text)
        self.terminal.print_blank_line()
        self.terminal.print_line("Press any key to continue...")
        
        self.terminal.wait_for_keypress()
        
        # Force room re-render after quest screen
        self._last_room_id = None
    
    def render_map_screen(self, map_display: str) -> None:
        """
        Render the map screen.
        
        Args:
            map_display: The ASCII map to display
        """
        self.clear_screen()
        
        self.terminal.print_line("*You close your eyes and retrace your steps…*")
        self.terminal.print_blank_line()
        self.terminal.print_line(map_display)
        self.terminal.print_blank_line()
        self.terminal.print_line("Press any key to continue...")
        
        self.terminal.wait_for_keypress()
        
        # Force room re-render after map screen
        self._last_room_id = None
    
    def force_room_redraw(self) -> None:
        """Force the next render to redraw the room."""
        self._last_room_id = None
