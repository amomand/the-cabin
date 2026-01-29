"""Terminal abstraction for cross-platform terminal operations."""

from __future__ import annotations

import os
import sys
from typing import Optional


class TerminalAdapter:
    """
    Abstract terminal operations for cross-platform compatibility.
    
    Handles raw mode, screen clearing, and "press any key" functionality
    with graceful fallbacks for non-TTY environments.
    """
    
    def __init__(self) -> None:
        self._is_tty = sys.stdin.isatty()
    
    @property
    def is_interactive(self) -> bool:
        """Check if we're running in an interactive terminal."""
        return self._is_tty
    
    def clear_screen(self) -> None:
        """Clear the terminal screen."""
        if os.name == 'nt':
            os.system('cls')
        else:
            os.system('clear')
    
    def wait_for_keypress(self, prompt: Optional[str] = None) -> None:
        """
        Wait for any key press.
        
        Args:
            prompt: Optional prompt to display (only shown on fallback)
        """
        if not self._is_tty:
            # Non-interactive - just continue
            return
        
        try:
            import tty
            import termios
            
            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            try:
                tty.setraw(fd)
                sys.stdin.read(1)
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        except (ImportError, termios.error, OSError, EOFError, AttributeError):
            # Fallback for Windows or non-interactive terminals
            try:
                if prompt:
                    input(prompt)
                else:
                    input("Press Enter to continue...")
            except EOFError:
                pass
    
    def print(self, text: str = "", end: str = "\n") -> None:
        """Print text to the terminal."""
        print(text, end=end)
    
    def print_line(self, text: str = "") -> None:
        """Print a line of text."""
        print(text)
    
    def print_blank_line(self) -> None:
        """Print a blank line."""
        print()
    
    def get_input(self, prompt: str = "> ") -> str:
        """Get input from the user."""
        try:
            return input(prompt)
        except EOFError:
            return "quit"
