import os
import sys
import tty
import termios
from typing import Iterable, List, Optional, Callable
from pathlib import Path


CUTSCENE_DISMISS_TEXT = "Pull yourself back."
CUTSCENE_DIRECTORY = Path(__file__).parent / "story" / "cutscenes"
AUTHORED_CUTSCENE_RULE = "─" * 79


class Cutscene:
    """Represents a single cut-scene with text and optional effects."""

    def __init__(
        self,
        text: str,
        trigger_condition: Optional[Callable] = None,
        cutscene_id: Optional[str] = None,
    ):
        self.text = text
        self.trigger_condition = trigger_condition
        self.has_played = False
        # Save identity. Falls back to a text prefix only for ad-hoc cutscenes
        # built in tests; every authored one is keyed by its filename, because
        # the authored files all open with the same 79-character rule and a
        # text prefix made them indistinguishable in a save.
        self.cutscene_id = cutscene_id or text[:50]
    
    def should_trigger(self, **context) -> bool:
        """Check if this cut-scene should trigger based on the current game state."""
        if self.has_played:
            return False
        
        if self.trigger_condition is None:
            return True
        
        return self.trigger_condition(**context)
    
    def play(self):
        """Display the cut-scene and wait for player input.

        No separator is printed here. Every authored cutscene file already
        opens and closes with its own rule, and `text` carries them, so the
        terminal was drawing a second one that the web overlay never had — a
        player-visible difference between the two surfaces in the middle of an
        authored scene.
        """
        self._clear_terminal()
        print(self.text)
        print()
        print(CUTSCENE_DISMISS_TEXT)
        
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

        # Load authored runtime assets. Their stable stems are also save IDs.
        self._load_cutscene_from_file("entering-cabin", self._cabin_entry_trigger)
        self._load_cutscene_from_file("lyer-encounter", self._lyer_encounter_trigger)
    
    def _load_cutscene_from_file(self, filename: str, trigger_condition: Optional[Callable] = None):
        """Load an authored cut-scene from the runtime data directory."""
        cutscene_path = CUTSCENE_DIRECTORY / f"{filename}.txt"
        cutscene_text = cutscene_path.read_text(encoding="utf-8")

        prefix = f"{AUTHORED_CUTSCENE_RULE}\n\n"
        suffix = f"\n\n{AUTHORED_CUTSCENE_RULE}\n"
        if not cutscene_text.startswith(prefix) or not cutscene_text.endswith(suffix):
            raise ValueError(
                f"Authored cut-scene {filename!r} is missing its required framing"
            )
        if not cutscene_text[len(prefix):-len(suffix)].strip():
            raise ValueError(f"Authored cut-scene {filename!r} has no story text")

        # Key by filename so save identity survives edits to the prose.
        self.cutscenes.append(
            Cutscene(cutscene_text, trigger_condition, cutscene_id=filename)
        )
    
    def _cabin_entry_trigger(self, from_room_id: str, to_room_id: str, **kwargs) -> bool:
        """Trigger when moving from the clearing to the cabin interior."""
        return from_room_id == "cabin_clearing" and to_room_id == "cabin_main"

    def _lyer_encounter_trigger(self, from_room_id: str, to_room_id: str, **kwargs) -> bool:
        """Trigger on the Act II climax teleport out of the old woods.

        `Map._trigger_lyer_encounter` sets the player down in `cabin_main`, and
        `old_woods` has no exit that reaches `cabin_main` in ordinary play, so
        this transition names the climax and nothing else. Coming back into the
        wrong cabin later is always `cabin_clearing -> cabin_main`, which does
        not match.

        The flight belongs in this channel rather than in the move's feedback
        because the surfaces render feedback *after* the destination room. As a
        cutscene it lands before the arrival, which is the order it is written
        in: she is chased into somewhere she should not be able to reach.
        """
        return from_room_id == "old_woods" and to_room_id == "cabin_main"
    
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

        Identifiers are `Cutscene.cutscene_id`, which for authored cutscenes is
        the source filename. They used to be the first 50 characters of the
        text, which was fine while there was one cutscene and became a silent
        data-loss bug the moment there were two: every authored cutscene file
        opens with the same 79-character rule, so both serialised to the same
        50 rule characters. Loading any save made after the cabin entry then
        marked the Act II flight as already played, and the climax fired as a
        wordless teleport.

        Saves written before this change carry the old rule-shaped identifier,
        which matches no cutscene and is ignored on load. Those runs replay a
        cutscene once, which is the cheaper failure by a wide margin.
        """
        return [cs.cutscene_id for cs in self.cutscenes if cs.has_played]

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
            cs.has_played = cs.cutscene_id in played
