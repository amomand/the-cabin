import os
import sys
import tty
import termios
from typing import Iterable, List, Optional, Callable
from pathlib import Path


class Cutscene:
    """Represents a single cut-scene with text and optional effects."""
    
    def __init__(self, text: str, trigger_condition: Optional[Callable] = None):
        self.text = text
        self.trigger_condition = trigger_condition
        self.has_played = False
    
    def should_trigger(self, **context) -> bool:
        """Check if this cut-scene should trigger based on the current game state."""
        if self.has_played:
            return False
        
        if self.trigger_condition is None:
            return True
        
        return self.trigger_condition(**context)
    
    def play(self):
        """Display the cut-scene and wait for player input."""
        self._clear_terminal()
        print(self.text)
        print("\n" + "─" * 80)  # Separator line
        print("Press any key to continue...")
        
        # Wait for any key press
        self._wait_for_key()
        self._clear_terminal()
        self.has_played = True
    
    def _clear_terminal(self):
        """Clear the terminal screen."""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def _wait_for_key(self):
        """Wait for any key press without showing the input."""
        # Save terminal settings
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        
        try:
            # Set terminal to raw mode
            tty.setraw(sys.stdin.fileno())
            # Wait for any key
            sys.stdin.read(1)
        finally:
            # Restore terminal settings
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


class CutsceneManager:
    """Manages all cut-scenes in the game."""
    
    def __init__(self):
        self.cutscenes: List[Cutscene] = []
        self._setup_cutscenes()
    
    def _setup_cutscenes(self):
        """Set up all cut-scenes for the game."""
        
        # Load cut-scenes from markdown files
        self._load_cutscene_from_file("entering-cabin", self._cabin_entry_trigger)
    
    def _load_cutscene_from_file(self, filename: str, trigger_condition: Optional[Callable] = None):
        """Load a cut-scene from a markdown file in the lore/cutscenes folder."""
        try:
            # Construct path to the cut-scene file
            cutscene_path = Path(__file__).parent.parent / "docs" / "lore" / "cutscenes" / f"{filename}.md"
            
            if not cutscene_path.exists():
                print(f"Warning: Cut-scene file not found: {cutscene_path}")
                return
            
            # Read the cut-scene text from the file
            with open(cutscene_path, 'r', encoding='utf-8') as file:
                content = file.read()
            
            # Extract the cut-scene text (everything after the first line)
            lines = content.split('\n')
            # Skip the title line and any metadata lines, start from the first decorative line
            start_index = 0
            for i, line in enumerate(lines):
                if line.startswith('─'):
                    start_index = i
                    break
            
            cutscene_text = '\n'.join(lines[start_index:])
            
            # Create and add the cut-scene
            cutscene = Cutscene(cutscene_text, trigger_condition)
            self.cutscenes.append(cutscene)
            
        except Exception as e:
            print(f"Error loading cut-scene {filename}: {e}")
    
    def _cabin_entry_trigger(self, from_room_id: str, to_room_id: str, **kwargs) -> bool:
        """Trigger when moving from the clearing to the cabin interior."""
        return from_room_id == "cabin_clearing" and to_room_id == "cabin_main"
    
    def check_and_play_cutscenes(self, from_room_id: str, to_room_id: str, **context):
        """Check if any cut-scenes should trigger and play them."""
        for cutscene in self.cutscenes:
            if cutscene.should_trigger(from_room_id=from_room_id, to_room_id=to_room_id, **context):
                cutscene.play()
                return True  # Return True if a cut-scene was played
        return False
    
    def add_cutscene(self, cutscene: Cutscene):
        """Add a new cut-scene to the manager."""
        self.cutscenes.append(cutscene)
    
    def reset_all_cutscenes(self):
        """Reset all cut-scenes so they can play again (useful for testing)."""
        for cutscene in self.cutscenes:
            cutscene.has_played = False

    def get_played_ids(self) -> List[str]:
        """Return stable identifiers for every cutscene currently marked as played.

        Identifiers use the first 50 chars of the cutscene text to match the
        format written by ``GameState.to_dict``. Keep this in sync with the
        serializer.
        """
        return [cs.text[:50] for cs in self.cutscenes if cs.has_played]

    def set_played_ids(self, played_ids: Iterable[str]) -> None:
        """Replace cutscene play state with the saved identifiers (authoritative).

        Used by ``GameState.from_dict`` to restore cutscene play state across
        save/load so authored beats do not re-fire on a loaded run. This is
        an authoritative replacement: cutscenes not in ``played_ids`` are
        explicitly reset to unplayed, so loading an older save into an
        existing manager (which is how ``GameEngine._load_game`` calls this)
        does not leave previously-played cutscenes marked as played.
        """
        played = set(played_ids)
        for cs in self.cutscenes:
            cs.has_played = cs.text[:50] in played
