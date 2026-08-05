"""WebGameSession -- state machine wrapping existing game components for web play."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional
from uuid import uuid4

from server.protocol import RenderFrame, SessionPhase

from game.player import Player
from game.map import Map
from game.cutscene import CUTSCENE_DISMISS_TEXT, CutsceneManager
from game.quests import create_quest_manager
from game.actions import create_default_registry
from game.events import EventBus
from game.events.types import PlayerMovedEvent
from game.events.listeners.quest_listener import QuestEventListener
from game.events.listeners.cutscene_listener import CutsceneEventListener
from game.death import death_line_for
from game.ending import ending_line_for, ending_reached
from game.input.handler import InputHandler, InputType
from game.ai_context import build_ai_context
from game import save_commands
from game.turn import apply_effects, handle_action_events, take_turn
from game.persistence import SaveManager


class WebCutsceneListener(CutsceneEventListener):
    """Cutscene listener that queues overlay frames instead of calling terminal I/O."""

    def __init__(self, session: "WebGameSession", **kwargs):
        super().__init__(**kwargs)
        self._session = session

    @staticmethod
    def _to_paragraphs(text: str) -> list[str]:
        """Join hard-wrapped continuation lines into paragraphs.

        Blank lines become empty-string entries (paragraph breaks).
        Decorative lines (───) are kept as-is.
        """
        result: list[str] = []
        buf: list[str] = []
        for raw in text.split("\n"):
            line = raw.rstrip()
            if line == "":
                if buf:
                    result.append(" ".join(buf))
                    buf = []
                result.append("")
            elif line.startswith("─"):
                if buf:
                    result.append(" ".join(buf))
                    buf = []
                result.append(line)
            else:
                buf.append(line)
        if buf:
            result.append(" ".join(buf))
        return result

    def _on_player_moved(self, event: PlayerMovedEvent) -> None:
        """Check for cutscenes on movement and queue overlay frames."""
        player = self.get_player()
        world_state = self.get_world_state()

        for cutscene in self.cutscene_manager.cutscenes:
            if cutscene.should_trigger(
                from_room_id=event.from_room_id,
                to_room_id=event.to_room_id,
                player=player,
                world_state=world_state,
            ):
                # Queue an overlay instead of calling cutscene.play()
                lines = self._to_paragraphs(cutscene.text)
                lines.extend(["", f"*{CUTSCENE_DISMISS_TEXT}*"])
                self._session._pending_overlays.append(
                    RenderFrame(
                        lines=lines,
                        clear=True,
                        wait_for_key=True,
                    )
                )
                cutscene.has_played = True
                return  # Only one cutscene per move


# Overlay cues, in the emphasised form the session queues them in. Each one
# tells the player to press a key to come back to the room.
_DISMISS_CUES = (f"*{CUTSCENE_DISMISS_TEXT}*", "*Hold the thought.*")


def _without_dismiss_cue(lines: List[str]) -> List[str]:
    """Drop a trailing dismiss cue and the blank line before it.

    Used when folding a queued overlay into a closing frame, where there is no
    keypress left to ask for.
    """
    kept = list(lines)
    if kept and kept[-1] in _DISMISS_CUES:
        kept.pop()
        if kept and kept[-1] == "":
            kept.pop()
    return kept


class WebGameSession:
    """A single web game session.

    State machine: INTRO_KEYPRESS -> AWAITING_INPUT <-> OVERLAY_KEYPRESS -> ENDED

    The core method ``handle_input(text)`` accepts a player command (or keypress
    acknowledgment) and returns a ``RenderFrame`` to send to the client.
    """

    def __init__(self) -> None:
        # Game components
        self.player = Player()
        self.map = Map()
        self.cutscene_manager = CutsceneManager()
        self.quest_manager = create_quest_manager()
        self.action_registry = create_default_registry()
        self.event_bus = EventBus()
        self.input_handler = InputHandler()
        self.save_manager = SaveManager(save_dir=Path("saves") / "web" / uuid4().hex)

        # Session state
        self.phase = SessionPhase.INTRO_KEYPRESS
        self._last_feedback: str = ""
        self._last_room_id: Optional[str] = None
        self._pending_overlays: List[RenderFrame] = []

        # Wire up event listeners
        self._setup_event_listeners()

    def _setup_event_listeners(self) -> None:
        """Register cutscenes before quests.

        Handlers run in registration order, so the cutscene queues its overlay
        first and the quest opening lands behind it. See
        `GameEngine._setup_event_listeners` for the reasoning. The two must not
        drift.
        """
        self._cutscene_listener = WebCutsceneListener(
            session=self,
            cutscene_manager=self.cutscene_manager,
            get_player=lambda: self.player,
            get_world_state=lambda: self.map.world_state,
        )
        self._cutscene_listener.register(self.event_bus)

        self._quest_listener = QuestEventListener(
            quest_manager=self.quest_manager,
            get_player=lambda: self.player,
            get_world_state=lambda: self.map.world_state,
            on_quest_triggered=self._on_quest_triggered,
            on_quest_updated=self._on_quest_updated,
            on_quest_completed=self._on_quest_completed,
        )
        self._quest_listener.register(self.event_bus)

    # -- Quest callbacks (mirror GameEngine) ----------------------------------

    def _on_quest_triggered(self, opening_text: str) -> None:
        self._pending_overlays.append(
            RenderFrame(
                lines=[
                    "*You take a breath and focus...*",
                    "",
                    opening_text,
                    "",
                    "*Hold the thought.*",
                ],
                clear=True,
                wait_for_key=True,
            )
        )

    def _on_quest_updated(self, update_text: str) -> None:
        self._last_feedback = update_text

    def _on_quest_completed(self, completion_text: str) -> None:
        self._last_feedback = completion_text

    # -- Public API -----------------------------------------------------------

    def get_intro_frame(self) -> RenderFrame:
        """Return the initial intro frame to send when a client connects."""
        return RenderFrame(
            lines=[
                "You shouldn't have come back.",
                "It's awake.",
                "It always has been.",
            ],
            clear=True,
            wait_for_key=True,
        )

    def handle_input(self, text: str) -> RenderFrame:
        """Process one round of player input and return the next frame.

        In INTRO_KEYPRESS / OVERLAY_KEYPRESS phases, ``text`` is ignored
        (any input counts as a keypress acknowledgment).
        """
        if self.phase == SessionPhase.ENDED:
            return RenderFrame(lines=["The cold has had its turn."], game_over=True)

        if self.phase == SessionPhase.INTRO_KEYPRESS:
            self.phase = SessionPhase.AWAITING_INPUT
            return self._render_room()

        if self.phase == SessionPhase.OVERLAY_KEYPRESS:
            # Overlay dismissed — force room re-render
            self._last_room_id = None
            # If more overlays are queued, show next one
            if self._pending_overlays:
                return self._pop_overlay()
            self.phase = SessionPhase.AWAITING_INPUT
            return self._render_room()

        # --- AWAITING_INPUT ---
        frame = self._process_game_input(text)

        # A closed run stays closed. An overlay queued in the same turn as a
        # death or an ending must not reopen the session behind the last word —
        # but it must not be thrown away either. The terminal prints cutscenes
        # inline as the turn runs, so a run that ends on the same turn as the
        # Act II flight still shows the flight there; dropping the queue here
        # deleted the scene on the web and nowhere else.
        #
        # Fold the queued lines into the final frame instead: the scene is
        # shown, in order, ahead of the closing words, and the session stays
        # shut with no keypress owed.
        #
        # The dismiss cue goes with it. "Pull yourself back." is an instruction
        # to press a key, and on a closing frame there is no key left to press.
        if self.phase == SessionPhase.ENDED:
            if self._pending_overlays:
                queued: List[str] = []
                for overlay in self._pending_overlays:
                    queued.extend(_without_dismiss_cue(overlay.lines))
                    queued.append("")
                frame.lines = queued + list(frame.lines)
                self._pending_overlays.clear()
            return frame

        # If processing produced overlay(s), show the first one
        if self._pending_overlays:
            # Prepend the game feedback (if any) so it isn't lost
            if frame and frame.lines:
                # We stash feedback; it will show after the overlay is dismissed
                pass
            return self._pop_overlay()

        return frame

    # -- Internal: game logic -------------------------------------------------

    def _process_game_input(self, text: str) -> RenderFrame:
        """Run one turn of the game loop for a text command."""
        # A blank command is not a turn. Keypress acknowledgments that race
        # in after an overlay has already been dismissed land here as empty
        # text; running them would send empty input to the interpreter and
        # append a second status line to the transcript.
        if not text.strip():
            return RenderFrame(lines=[], prompt="> ")

        parsed = self.input_handler.parse(text)

        if parsed.input_type == InputType.QUIT:
            self.phase = SessionPhase.ENDED
            return RenderFrame(
                lines=["The cold watches you go."],
                clear=True,
                game_over=True,
            )

        if parsed.input_type == InputType.QUEST_SCREEN:
            self._pending_overlays.append(
                RenderFrame(
                    lines=[
                        "*You take a breath and focus...*",
                        "",
                        self.quest_manager.get_active_quest_display(),
                        "",
                        "*Hold the thought.*",
                    ],
                    clear=True,
                    wait_for_key=True,
                )
            )
            return self._pop_overlay()

        if parsed.input_type == InputType.MAP_SCREEN:
            visited = self.map.get_visited_rooms()
            map_display = self.map.display_map(visited)
            self._pending_overlays.append(
                RenderFrame(
                    lines=[
                        "*You close your eyes and retrace your steps...*",
                        "",
                        map_display,
                        "",
                        "*Open your eyes.*",
                    ],
                    clear=True,
                    wait_for_key=True,
                )
            )
            return self._pop_overlay()

        if parsed.input_type == InputType.SAVE:
            self._save_game(parsed.slot_name or "autosave")
            return self._render_room()

        if parsed.input_type == InputType.LOAD:
            self._load_game(parsed.slot_name or "autosave")
            # A loaded save may already be at the death threshold, or the
            # story may already be finished — mirrors
            # GameEngine.handle_user_input's post-load checks.
            death_frame = self._death_frame_if_dead()
            if death_frame is not None:
                return death_frame
            ending_frame = self._ending_frame_if_over()
            if ending_frame is not None:
                return ending_frame
            return self._render_room()

        if parsed.input_type == InputType.LIST_SAVES:
            self._list_saves()
            return self._render_room()

        if parsed.input_type == InputType.DELETE_SAVE:
            self._delete_save(parsed.slot_name or "autosave")
            return self._render_room()

        # --- Game action: shared turn core, one implementation for both surfaces
        take_turn(
            text,
            player=self.player,
            game_map=self.map,
            quest_manager=self.quest_manager,
            action_registry=self.action_registry,
            event_bus=self.event_bus,
            set_feedback=self._set_feedback,
        )

        # Check if player died — shared precedence and lines with the terminal.
        # Death is checked first so a turn that lands both ends as a death.
        death_frame = self._death_frame_if_dead()
        if death_frame is not None:
            return death_frame

        ending_frame = self._ending_frame_if_over()
        if ending_frame is not None:
            return ending_frame

        return self._render_room()

    def _ending_frame_if_over(self) -> Optional[RenderFrame]:
        """End the session and build the closing frame if the story finished.

        Mirrors `_death_frame_if_dead`; the closing lines come from
        `game.ending.ending_line_for` so terminal and web stay in sync.
        """
        line = ending_line_for(self.map.world_state)
        if not ending_reached(self.map.world_state):
            return None
        self.phase = SessionPhase.ENDED
        lines = [self._last_feedback] if self._last_feedback else []
        if line is not None:
            lines.extend(["", line])
        self._last_feedback = ""
        return RenderFrame(
            lines=lines,
            clear=True,
            game_over=True,
        )

    def _death_frame_if_dead(self) -> Optional[RenderFrame]:
        """End the session and build the closing frame if the player is dead.

        One implementation for every death exit (post-action and post-load),
        so the two cannot drift apart.
        """
        death_line = death_line_for(self.player)
        if death_line is None:
            return None
        self.phase = SessionPhase.ENDED
        return RenderFrame(
            lines=[
                self._last_feedback,
                "",
                death_line,
            ],
            clear=True,
            game_over=True,
        )

    def _build_ai_context(self) -> dict:
        """Build the context payload sent to the AI interpreter."""
        return build_ai_context(self.player, self.map, self.quest_manager)

    def _set_feedback(self, text: str) -> None:
        """Feedback channel handed to the shared turn core."""
        self._last_feedback = text

    def _save_game(self, slot_name: str) -> None:
        """Save game state from a web session."""
        self._last_feedback = save_commands.save_game(
            self.save_manager,
            slot_name,
            player=self.player,
            game_map=self.map,
            quest_manager=self.quest_manager,
            cutscene_manager=self.cutscene_manager,
        )

    def _list_saves(self) -> None:
        """Show the player every save slot they have on disk."""
        self._last_feedback = save_commands.list_saves(self.save_manager)

    def _delete_save(self, slot_name: str) -> None:
        """Delete a save slot, if it exists."""
        self._last_feedback = save_commands.delete_save(self.save_manager, slot_name)

    def _load_game(self, slot_name: str) -> None:
        """Load a normal save, falling back to permanent dev seed names."""
        outcome = save_commands.load_game(
            self.save_manager,
            slot_name,
            player=self.player,
            game_map=self.map,
            quest_manager=self.quest_manager,
            cutscene_manager=self.cutscene_manager,
        )
        if outcome.loaded:
            self._pending_overlays.clear()
            self.phase = SessionPhase.AWAITING_INPUT
            self._last_room_id = None
        self._last_feedback = outcome.feedback

    def _apply_effects(self, intent, skip_inventory: bool = False) -> None:
        """Apply an intent's effects. Thin wrapper over the shared turn core.

        Retained as a per-surface seam for tests, which is what lets the
        parity suite compare the two surfaces; production goes through
        `turn.take_turn` directly.
        """
        apply_effects(intent, self.player, self.map, skip_inventory=skip_inventory)

    def _handle_action_events(self, result, intent=None) -> None:
        """Emit an action result's events. Thin wrapper over the shared turn core.

        Retained as a per-surface seam for tests, which is what lets the
        parity suite compare the two surfaces; production goes through
        `turn.take_turn` directly.
        """
        handle_action_events(result, self.player, self.map, self.event_bus)

    # -- Rendering helpers ----------------------------------------------------

    def _render_room(self) -> RenderFrame:
        """Build a RenderFrame for the current room state."""
        room = self.map.current_room
        room_changed = room.id != self._last_room_id

        lines: List[str] = []

        if room_changed:
            self._last_room_id = room.id
            description = room.get_description(self.player, self.map.world_state)
            lines.append(room.name)
            lines.append("-" * len(room.name))
            lines.append(description)
            lines.append("")

        if self._last_feedback:
            if not room_changed:
                lines.append("")
            lines.append(self._last_feedback)
            lines.append("")
            self._last_feedback = ""

        lines.append(f"Health: {self.player.health}    Fear: {self.player.fear}")

        return RenderFrame(
            lines=lines,
            clear=room_changed,
            prompt="> ",
        )

    def _pop_overlay(self) -> RenderFrame:
        """Pop the next pending overlay and transition to OVERLAY_KEYPRESS."""
        frame = self._pending_overlays.pop(0)
        self.phase = SessionPhase.OVERLAY_KEYPRESS
        return frame
