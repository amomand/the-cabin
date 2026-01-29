"""
Thin game loop orchestrator for The Cabin.

This module provides a clean separation of concerns by delegating
all work to injected components. The GameLoop itself is under 100 lines.
"""

from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from game.player import Player
from game.map import Map
from game.cutscene import CutsceneManager
from game.quests import create_quest_manager
from game.actions import create_default_registry
from game.events import EventBus
from game.events.listeners.quest_listener import QuestEventListener
from game.events.listeners.cutscene_listener import CutsceneEventListener
from game.render import RenderManager
from game.input import InputHandler, InputType
from game.effects import EffectManager
from game.persistence import SaveManager
from game.game_state import GameState
from game.ai_interpreter import interpret, ALLOWED_ACTIONS

if TYPE_CHECKING:
    from game.actions import ActionRegistry


class GameLoop:
    """
    Thin orchestrator for the game loop.
    
    Coordinates: render → input → execute → effects → events
    All logic is delegated to injected components.
    """
    
    def __init__(
        self,
        player: Optional[Player] = None,
        game_map: Optional[Map] = None,
        render_manager: Optional[RenderManager] = None,
        input_handler: Optional[InputHandler] = None,
        effect_manager: Optional[EffectManager] = None,
        action_registry: Optional["ActionRegistry"] = None,
        event_bus: Optional[EventBus] = None,
        save_manager: Optional[SaveManager] = None,
        cutscene_manager: Optional[CutsceneManager] = None,
        quest_manager = None,
    ):
        """Initialize game loop with optional dependency injection."""
        self.running = True
        self.player = player or Player()
        self.map = game_map or Map()
        self.render = render_manager or RenderManager()
        self.input = input_handler or InputHandler()
        self.effects = effect_manager or EffectManager()
        self.actions = action_registry or create_default_registry()
        self.event_bus = event_bus or EventBus()
        self.saves = save_manager or SaveManager()
        self.cutscenes = cutscene_manager or CutsceneManager()
        self.quests = quest_manager or create_quest_manager()
        self._feedback = ""
        
        self._setup_listeners()
    
    def _setup_listeners(self) -> None:
        """Configure event listeners."""
        self._quest_listener = QuestEventListener(
            quest_manager=self.quests,
            get_player=lambda: self.player,
            get_world_state=lambda: self.map.world_state,
            on_quest_triggered=lambda text: self.render.render_quest_screen(text),
            on_quest_updated=lambda text: setattr(self, '_feedback', f"Quest Update: {text}"),
            on_quest_completed=lambda text: setattr(self, '_feedback', f"Quest Complete: {text}"),
        )
        self._quest_listener.register(self.event_bus)
        
        self._cutscene_listener = CutsceneEventListener(
            cutscene_manager=self.cutscenes,
            get_player=lambda: self.player,
            get_world_state=lambda: self.map.world_state,
        )
        self._cutscene_listener.register(self.event_bus)
    
    def run(self) -> None:
        """Main game loop."""
        self.render.render_intro()
        
        while self.running:
            room = self.map.current_room
            self.render.render_room(room, self.player, self.map.world_state, self._feedback)
            self._feedback = ""
            
            user_input = input("> ")
            self._process_input(user_input)
    
    def _process_input(self, user_input: str) -> None:
        """Route input to appropriate handler."""
        parsed = self.input.parse(user_input)
        
        if parsed.input_type == InputType.QUIT:
            self.running = False
        elif parsed.input_type == InputType.QUEST_SCREEN:
            self.render.render_quest_screen(self.quests.get_active_quest_display())
            self.render.force_room_redraw()
        elif parsed.input_type == InputType.MAP_SCREEN:
            self._show_map()
        elif parsed.input_type == InputType.SAVE:
            self._save(parsed.slot_name)
        elif parsed.input_type == InputType.LOAD:
            self._load(parsed.slot_name)
        else:
            self._execute_action(user_input)
    
    def _execute_action(self, user_input: str) -> None:
        """Execute a game action via AI interpretation."""
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
        
        intent = interpret(user_input, context)
        self.effects.apply_intent_effects(self.player, room, getattr(intent, 'effects', {}), self.map.items)
        
        result = self.actions.execute(intent.action, self.player, self.map, intent)
        
        if result is None:
            self._feedback = intent.reply or "You start, then think better of it."
        else:
            self._feedback = result.feedback
    
    def _save(self, slot_name: str) -> None:
        """Save game state."""
        state = GameState(self.player, self.map, self.quests, self.map.world_state)
        self.saves.save_game(state, slot_name)
        self._feedback = f"Game saved to {slot_name}."
    
    def _load(self, slot_name: str) -> None:
        """Load game state."""
        data = self.saves.load_game(slot_name)
        if data is None:
            self._feedback = f"No save found: {slot_name}"
            return
        
        player_data = data.get("player", {})
        self.player.health = player_data.get("health", 100)
        self.player.fear = player_data.get("fear", 0)
        
        map_data = data.get("map", {})
        room_id = map_data.get("current_room_id")
        if room_id and room_id in self.map.rooms:
            self.map.current_room = self.map.rooms[room_id]
        
        self.render.force_room_redraw()
        self._feedback = f"Game loaded from {slot_name}."
    
    def _show_map(self) -> None:
        """Display the map screen."""
        visited = self.map.get_visited_rooms()
        map_display = self.map.display_map(visited)
        self.render.render_quest_screen(f"*You retrace your steps...*\n\n{map_display}")
        self.render.force_room_redraw()
