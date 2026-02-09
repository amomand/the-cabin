"""WebGameSession — state machine wrapping existing game components for web play."""

from __future__ import annotations

from typing import List, Optional

from server.protocol import RenderFrame, SessionPhase

from game.player import Player
from game.map import Map
from game.cutscene import CutsceneManager
from game.quests import create_quest_manager
from game.actions import create_default_registry
from game.events import EventBus
from game.events.types import (
    PlayerMovedEvent, ItemTakenEvent, ItemDroppedEvent, ItemThrownEvent,
    PowerRestoredEvent, FireLitEvent, FireAttemptEvent,
    LightSwitchUsedEvent, FireplaceUsedEvent, FuelGatheredEvent,
    WildlifeProvokedEvent,
)
from game.events.listeners.quest_listener import QuestEventListener
from game.events.listeners.cutscene_listener import CutsceneEventListener
from game.input.handler import InputHandler, InputType
from game.ai_interpreter import interpret, ALLOWED_ACTIONS


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
                self._session._pending_overlays.append(
                    RenderFrame(
                        lines=lines,
                        clear=True,
                        wait_for_key=True,
                    )
                )
                cutscene.has_played = True
                return  # Only one cutscene per move


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

        # Session state
        self.phase = SessionPhase.INTRO_KEYPRESS
        self._last_feedback: str = ""
        self._last_room_id: Optional[str] = None
        self._pending_overlays: List[RenderFrame] = []

        # Wire up event listeners
        self._setup_event_listeners()

    def _setup_event_listeners(self) -> None:
        self._quest_listener = QuestEventListener(
            quest_manager=self.quest_manager,
            get_player=lambda: self.player,
            get_world_state=lambda: self.map.world_state,
            on_quest_triggered=self._on_quest_triggered,
            on_quest_updated=self._on_quest_updated,
            on_quest_completed=self._on_quest_completed,
        )
        self._quest_listener.register(self.event_bus)

        self._cutscene_listener = WebCutsceneListener(
            session=self,
            cutscene_manager=self.cutscene_manager,
            get_player=lambda: self.player,
            get_world_state=lambda: self.map.world_state,
        )
        self._cutscene_listener.register(self.event_bus)

    # -- Quest callbacks (mirror GameEngine) ----------------------------------

    def _on_quest_triggered(self, opening_text: str) -> None:
        self._pending_overlays.append(
            RenderFrame(
                lines=[
                    "*You take a breath and focus...*",
                    "",
                    opening_text,
                    "",
                    "Press any key to continue...",
                ],
                clear=True,
                wait_for_key=True,
            )
        )

    def _on_quest_updated(self, update_text: str) -> None:
        self._last_feedback = f"Quest Update: {update_text}"

    def _on_quest_completed(self, completion_text: str) -> None:
        self._last_feedback = f"Quest Complete: {completion_text}"

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
            return RenderFrame(lines=["The session has ended."], game_over=True)

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
                        "Press any key to continue...",
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
                        "Press any key to continue...",
                    ],
                    clear=True,
                    wait_for_key=True,
                )
            )
            return self._pop_overlay()

        if parsed.input_type in (InputType.SAVE, InputType.LOAD):
            self._last_feedback = "The wilderness doesn't keep records. There is only forward."
            return self._render_room()

        # --- Game action: interpret via AI / rule-based -----------------------
        room = self.map.current_room
        context = {
            "room_name": room.name,
            "exits": list(room.exits.keys()),
            "room_items": [item.name for item in room.items],
            "room_wildlife": [animal.name for animal in room.wildlife],
            "inventory": self.player.get_inventory_names(),
            "world_flags": self.map.world_state.to_dict(),
            "allowed_actions": list(ALLOWED_ACTIONS),
        }

        intent = interpret(text, context)

        # Apply AI-suggested effects
        self._apply_effects(intent)

        # Execute action via registry
        result = self.action_registry.execute(
            intent.action, self.player, self.map, intent
        )

        if result is None:
            self._last_feedback = (
                intent.reply
                or "You start, then think better of it. The cold in your chest makes you careful."
            )
        else:
            self._last_feedback = result.feedback
            self._handle_action_events(result, intent)

        # Check if player died
        if self.player.health <= 0:
            self.phase = SessionPhase.ENDED
            return RenderFrame(
                lines=[
                    self._last_feedback,
                    "",
                    "The darkness claims you. You are gone.",
                ],
                clear=True,
                game_over=True,
            )

        if self.player.fear >= 100:
            self.phase = SessionPhase.ENDED
            return RenderFrame(
                lines=[
                    self._last_feedback,
                    "",
                    "The fear swallows you whole. You cannot move. You cannot think.",
                ],
                clear=True,
                game_over=True,
            )

        return self._render_room()

    def _apply_effects(self, intent) -> None:
        """Apply fear/health/inventory effects from an intent. Mirrors GameEngine._apply_effects."""
        effects = getattr(intent, "effects", None) or {}
        fear_delta = max(-2, min(2, int(effects.get("fear", 0))))
        health_delta = max(-2, min(2, int(effects.get("health", 0))))

        self.player.fear = max(0, min(100, self.player.fear + fear_delta))
        self.player.health = max(0, min(100, self.player.health + health_delta))

        inventory_remove = [str(x) for x in effects.get("inventory_remove", [])]
        for item_name in inventory_remove:
            self.player.remove_item(item_name)

        inventory_add = [str(x) for x in effects.get("inventory_add", [])]
        room = self.map.current_room
        for item_name in inventory_add:
            if item_name in self.map.items and room.has_item(item_name):
                item = room.remove_item(item_name)
                if item and item.is_carryable():
                    self.player.add_item(item)

    def _handle_action_events(self, result, intent) -> None:
        """Convert action result events to GameEvent objects and emit. Mirrors GameEngine."""
        state_changes = result.state_changes or {}

        for event_name in result.events:
            if event_name == "player_moved":
                self.event_bus.emit(PlayerMovedEvent(
                    from_room_id=state_changes.get("from_room_id", ""),
                    to_room_id=state_changes.get("to_room_id", ""),
                    direction=state_changes.get("direction", ""),
                ))
            elif event_name == "item_taken":
                self.event_bus.emit(ItemTakenEvent(
                    item_name=state_changes.get("item_name", ""),
                    room_id=self.map.current_room.id,
                ))
            elif event_name == "fuel_gathered":
                self.event_bus.emit(FuelGatheredEvent(
                    item_name=state_changes.get("item_name", "firewood"),
                ))
            elif event_name == "item_dropped":
                self.event_bus.emit(ItemDroppedEvent(
                    item_name=state_changes.get("item_name", ""),
                    room_id=self.map.current_room.id,
                ))
            elif event_name == "item_thrown":
                self.event_bus.emit(ItemThrownEvent(
                    item_name=state_changes.get("item_name", ""),
                    target=state_changes.get("target"),
                    into_darkness=False,
                ))
            elif event_name == "thrown_into_darkness":
                fear_increase = state_changes.get("fear_increase", 5)
                self.player.fear = min(100, self.player.fear + fear_increase)
            elif event_name == "power_restored":
                self.event_bus.emit(PowerRestoredEvent())
            elif event_name == "fire_lit":
                self.event_bus.emit(FireLitEvent())
            elif event_name == "fire_no_fuel":
                self.event_bus.emit(FireAttemptEvent(has_fuel=False, has_matches=True))
            elif event_name == "use_light_switch_no_power":
                self.event_bus.emit(LightSwitchUsedEvent(has_power=False))
            elif event_name == "lights_on":
                self.event_bus.emit(LightSwitchUsedEvent(has_power=True))
            elif event_name == "use_fireplace_no_fuel":
                self.event_bus.emit(FireplaceUsedEvent(has_fuel=False))
            elif event_name == "use_fireplace":
                self.event_bus.emit(FireplaceUsedEvent(has_fuel=True))
            elif event_name == "wildlife_provoked":
                self.event_bus.emit(WildlifeProvokedEvent(
                    wildlife_name=state_changes.get("target", ""),
                    action=state_changes.get("provoke_result", "ignore"),
                ))
            elif event_name == "wildlife_attack":
                health_damage = state_changes.get("health_damage", 0)
                fear_increase = state_changes.get("fear_increase", 0)
                self.player.health = max(0, self.player.health - health_damage)
                self.player.fear = min(100, self.player.fear + fear_increase)

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
        lines.append("")
        lines.append("What would you like to do?")

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
