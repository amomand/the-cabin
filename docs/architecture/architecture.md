# The Cabin - Architecture Documentation

**Version:** 2.0  
**Last Updated:** January 29, 2026

> **Note:** This document was updated after the Phase 1-5 refactoring to reflect the new modular architecture. See `developer-guide.md` for implementation details.

---

## Table of Contents

1. [Overview](#overview)
2. [Design Philosophy](#design-philosophy)
3. [High-Level Architecture](#high-level-architecture)
4. [Core Components](#core-components)
5. [Data Flow](#data-flow)
6. [Separation of Concerns](#separation-of-concerns)
7. [Key Design Patterns](#key-design-patterns)
8. [Module Dependencies](#module-dependencies)
9. [Extension Points](#extension-points)
10. [State Management](#state-management)

---

## Overview

**The Cabin** is a survival horror text adventure game built in Python. It emphasizes atmospheric immersion, diegetic narration (no fourth-wall breaking), and player agency through natural language input. The game runs entirely in the terminal, clearing the screen between room transitions to create a sense of isolation and exploration.

### Core Technologies

- **Python 3.10+**: Core runtime
- **OpenAI API (gpt-5.2-mini)**: Natural language interpretation
- **python-dotenv**: Environment variable management
- **httpx**: HTTP client for API calls
- **Native terminal**: No UI frameworks - raw terminal interaction
- **pytest**: Test framework (231 tests)

### Key Features

- Free-text natural language input with AI-powered interpretation
- Hierarchical world structure: Map → Locations → Rooms
- Procedural room descriptions that respond to world state
- Quest system with triggers, updates, and completion conditions
- Inventory and item system with trait-based behavior
- Wildlife system with behavioral AI
- Cutscene system for narrative moments
- Fear and health mechanics
- Exit requirements system for gated progression
- **Save/Load system** with JSON persistence
- **Event-driven architecture** for decoupled quest/cutscene integration
- **Modular action system** with registry-based dispatch
- **Response caching** for repeated commands

---

## Design Philosophy

### Diegetic Immersion (CRITICAL)

Every element of the game stays "in-world." No meta-commentary, no system messages, no UI chrome. All feedback is given in second-person, present tense, as if the player is living the experience.

**The AI is the core experience, not a fallback.**

**Example:**
- ❌ "Invalid command. Please enter a valid direction."
- ❌ "You can't do that here."
- ✅ "You turn that way and stop. Just trees and dark."
- ✅ "You tense your legs, willing yourself upward. Gravity wins."

See: `docs/game_mechanics/diegetic_action_interpretor.md`

### Atmospheric Restraint

The game relies on subtlety and implication rather than explicit horror. Silence, cold, and isolation are tools. The terminal clearing between rooms reinforces the sense of moving through a hostile, empty world.

### Player Agency with Constraints

Players can type anything, but the game enforces realistic constraints through diegetic denial. Impossible actions fail naturally within the fiction rather than through error messages.

### Separation of Content and Logic

Game content (room descriptions, items, quests) is defined separately from game logic (movement, state management, input handling). This allows for easy expansion and modification without touching core systems.

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                          main.py                                 │
│                      (Entry Point)                               │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    GameEngine / GameLoop                         │
│  • Coordinates render → input → execute → effects cycle          │
│  • Delegates ALL work to injected components                     │
│  • GameLoop is <160 lines (thin orchestrator)                    │
└──┬──────────┬──────────┬──────────┬──────────┬─────────────────┘
   │          │          │          │          │
   ▼          ▼          ▼          ▼          ▼
┌──────┐ ┌────────┐ ┌─────────┐ ┌────────┐ ┌─────────┐
│Render││ Input  ││ Action  ││ Effect ││  Event  │
│Mgr   ││ Handler││ Registry││ Manager││  Bus    │
└──────┘ └────────┘ └────┬────┘ └────────┘ └────┬────┘
                         │                      │
                         ▼                      ▼
                  ┌─────────────┐        ┌─────────────┐
                  │   Actions   │        │  Listeners  │
                  │ (13 classes)│        │ Quest/Scene │
                  └─────────────┘        └─────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                        GameState                                 │
│  • Player (health, fear, inventory)                              │
│  • WorldState (typed flags: has_power, fire_lit, etc.)           │
│  • Map (current room, visited rooms)                             │
│  • QuestManager (active, completed)                              │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                      AI Interpreter                              │
│  • gpt-5.2-mini for creative/impossible input                    │
│  • Response caching (LRU, 50 entries)                            │
│  • Rule-based fallback for trivial commands                      │
└─────────────────────────────────────────────────────────────────┘
```

### Layer Breakdown

1. **Entry Layer** (`main.py`): Minimal entry point that instantiates and runs the game engine
2. **Orchestration Layer** (`game_engine.py`, `game_loop.py`): Thin coordinators, delegate to subsystems
3. **Component Layer** (`actions/`, `events/`, `render/`, `input/`, `effects/`, `persistence/`): Modular, testable components
4. **Domain Layer** (`map.py`, `player.py`, `quest.py`, etc.): Core game logic and state
5. **Content Layer** (within domain files): Actual game content (rooms, items, quests)
6. **External Services Layer** (`ai_interpreter.py`): Integration with OpenAI API

---

## Core Components

### 1. GameEngine / GameLoop

**Responsibility:** Orchestrates the game loop cycle.

**After refactoring:**
- `GameEngine` remains for backward compatibility (~430 lines)
- `GameLoop` is the new thin orchestrator (~160 lines)
- Both delegate work to injected components

**Key Methods:**
- `run()`: Main game loop - render, accept input, update state, repeat
- `handle_user_input()` / `_process_input()`: Routes input to appropriate handler
- `_save_game()`, `_load_game()`: Persistence operations

**Injected Dependencies:**
- `ActionRegistry` - Dispatches to action classes
- `EventBus` - Pub/sub event system
- `SaveManager` - JSON persistence
- `RenderManager` - Display abstraction (GameLoop only)
- `InputHandler` - Input routing
- `EffectManager` - Apply fear/health changes

### 2. ActionRegistry (`game/actions/`)

**Responsibility:** Maps action names to Action classes and executes them.

**Actions (13 classes):**
- `MoveAction` - Player movement
- `LookAction`, `ListenAction` - Observation
- `TakeAction`, `DropAction`, `InventoryAction` - Inventory management
- `ThrowAction` - Throwing items at wildlife
- `UseAction` - Using items (circuit breaker, matches)
- `LightAction` - Lighting fires
- `HelpAction` - Show help text

**Pattern:**
```python
result = registry.execute("move", player, map, intent)
# Returns ActionResult with: success, feedback, events, state_changes
```

### 3. EventBus (`game/events/`)

**Responsibility:** Decoupled pub/sub event system.

**Events (15 types):**
- `PlayerMovedEvent`, `ItemTakenEvent`, `ItemDroppedEvent`
- `PowerRestoredEvent`, `FireLitEvent`, `FuelGatheredEvent`
- `WildlifeProvokedEvent`, etc.

**Listeners:**
- `QuestEventListener` - Triggers/updates/completes quests
- `CutsceneEventListener` - Triggers cutscenes on movement

### 4. AI Interpreter (`game/ai_interpreter.py`)

**Responsibility:** Converts natural language to structured Intent.

**Key Features:**
- Uses `gpt-5.2-mini` (configurable)
- Response caching (LRU, 50 entries)
- Rule-based fallback for trivial commands
- Diegetic responses for impossible actions

**Critical:** The AI is the core experience. It handles ALL creative, ambiguous, or impossible input with in-world narrative responses.

### 5. Persistence (`game/persistence/`)

**Responsibility:** Save/load game state.

**SaveManager methods:**
- `save_game(game_state, slot_name)` → JSON file
- `load_game(slot_name)` → GameState dict
- `list_saves()`, `delete_save()`, `save_exists()`

---

### 6. Map (`map.py`)

**Responsibility:** Manages the game world structure and player navigation.

**Hierarchy:**
```
Map
 ├── world_state: WorldState           # Typed flags (has_power, fire_lit, etc.)
 ├── visited_rooms: Set[str]           # Tracking exploration
 ├── locations: Dict[str, Location]    # Top-level areas
 └── current_location_id, current_room_id
```

**WorldState (`game/world_state.py`):**
- Typed dataclass with explicit fields
- Dict-style access for backward compatibility
- Validation method
- Serialization support (`to_dict()`, `from_dict()`)

**Key Methods:**
- `move(direction)`: Handles movement between rooms, checks requirements
- `display_map(visited_rooms)`: Generates ASCII map visualization
- `get_visited_rooms()`: Returns exploration state

**Location & Room Management:**
- Locations are containers for related rooms (wilderness, cabin_interior, cabin_grounds)
- Rooms are actual explorable spaces with descriptions, items, wildlife, and exits
- Room exits can cross location boundaries: `("target_location_id", "target_room_id")`

**Design Notes:**
- Movement is always room-to-room; location transitions are automatic
- World state is centralized here for easy access by all systems
- Requirements system allows gating exits (need items, flags, fear thresholds)
- Map tracks visited rooms for persistence and visualization

---

### 3. Room (`room.py`)

**Responsibility:** Represents a single explorable space.

**Attributes:**
- `id`, `name`: Identification
- `static_description`: Base room text
- `exits`: Dict mapping directions to (location_id, room_id) tuples
- `exit_criteria`: List of Requirements that must be met to leave
- `items`: List of Item objects currently in the room
- `wildlife`: List of Wildlife objects currently in the room
- `_description_fn`: Optional procedural description function

**Key Methods:**
- `get_description(player, world_state)`: Generates current room description
- `get_items_description()`: Describes visible items
- `add_item()`, `remove_item()`, `has_item()`, `get_item()`: Item management
- `add_wildlife()`, `remove_wildlife()`, `has_wildlife()`, `get_wildlife()`: Wildlife management
- `get_visible_wildlife()`: Returns non-elusive wildlife
- `get_audible_wildlife()`: Returns wildlife that can be heard
- `on_enter(player, world_state)`: Hook for room entry effects

**Design Notes:**
- Descriptions can be static or procedurally generated based on state
- Items are no longer auto-included in room descriptions (handled by AI interpreter)
- Wildlife can be visible, audible, or elusive (heard but not seen)
- Name cleaning utilities remove articles ("a", "an", "the") for flexible input

---

### 4. Location (`location.py`)

**Responsibility:** Container for related rooms, representing larger areas.

**Attributes:**
- `id`, `name`: Identification
- `overview_description`: Location-level description (can be static or callable)
- `rooms`: Dict of Room objects
- `exits`: Dict of location-level exits (sparingly used)
- `exit_criteria`: List of Requirements (sparingly used - prefer room-level)

**Key Methods:**
- `add_room(room)`: Register a room to this location
- `get_overview_text(world_state)`: Get location description

**Design Notes:**
- Locations are organizational containers, not directly navigated
- Most navigation and requirements are at the room level
- Exit criteria at location level is possible but discouraged (use room criteria instead)

---

### 5. Player (`player.py`)

**Responsibility:** Manages player state and inventory.

**Attributes:**
- `name`: Player character name ("Eli")
- `health`: 0-100, physical condition
- `fear`: 0-100, mental state
- `inventory`: List[Item] - carried items

**Key Methods:**
- `add_item(item)`, `remove_item(item_name)`: Inventory management
- `get_item(item_name)`: Check inventory without removing
- `has_item(item_name)`: Boolean check for item possession
- `get_inventory_names()`: Returns list of item names for display
- `_clean_item_name(item_name)`: Normalizes item names (removes articles)

**Design Notes:**
- Simple state container, no complex logic
- Health and fear are clamped 0-100
- Item name matching is flexible (ignores "a", "an", "the")
- No weight or slot limits currently implemented (future extension point)

---

### 6. Item (`item.py`)

**Responsibility:** Represents objects that can be interacted with.

**Trait System:**
Items have a set of traits that define their behavior:
- `carryable`: Can be picked up
- `usable`: Can be used/interacted with
- `throwable`: Can be thrown
- `weapon`: Can be used for combat
- `flammable`: Can catch fire
- `edible`: Can be consumed
- `cursed`: Has supernatural effects

**Attributes:**
- `name`: Item identifier
- `description`: Detailed description
- `traits`: Set[str] - behavioral tags
- `room_description`: How it appears in room text

**Key Methods:**
- `has_trait(trait)`: Check for specific trait
- Trait checkers: `is_carryable()`, `is_usable()`, `is_throwable()`, etc.

**Predefined Items:**
Created via `create_items()` in item.py:
- Survival items: rope, matches, key, stone, stick, knife, berries, amulet
- Quest items: firewood, circuit_breaker
- Room features: light_switch, fireplace

**Design Notes:**
- Trait-based system allows flexible behavior without subclassing
- Items can have multiple traits (stone is carryable, throwable, and weapon)
- Room features (like fireplaces) are items with no carryable trait
- Easy to extend by adding new traits

---

### 7. Wildlife (`wildlife.py`)

**Responsibility:** Represents living creatures in the game world.

**Trait System:**
- `docile`: Friendly or neutral
- `vicious`: Will attack when provoked
- `skittish`: Will flee when threatened
- `ambient`: Background presence
- `massive`: Large creature
- `elusive`: Can be heard but not seen
- Additional traits: `curious`, `fast`, `pack`, `solitary`, `silent`, `predatory`, `nocturnal`, `arboreal`, `watchful`, `symbolic`, `startling`, `thief`, `tough`

**Attributes:**
- `name`: Wildlife identifier
- `description`: Detailed description
- `traits`: Set[str] - behavioral tags
- `sound_description`: What it sounds like
- `visual_description`: What it looks like when seen
- `has_attacked`: Tracks if already attacked player

**Key Methods:**
- `has_trait(trait)`: Check for specific trait
- Trait checkers: `is_docile()`, `is_vicious()`, `is_skittish()`, `is_elusive()`, etc.
- `can_attack()`: Check if can attack (vicious and hasn't attacked yet)
- `provoke()`: Returns result of provoking the animal (attack/flee/wander/ignore)

**Predefined Wildlife:**
Created via `create_wildlife()` in wildlife.py:
- Docile: reindeer, fox, mountain_hare
- Vicious: wolf, brown_bear, wolverine
- Elusive: eurasian_lynx, pine_marten
- Ambient: snowy_owl, eagle_owl, raven, capercaillie

**Procedural Wildlife:**
- `get_random_wildlife(wildlife_pool, max_count)`: Randomly selects wildlife for rooms

**Design Notes:**
- Similar trait-based system to Items
- Behavioral responses defined in `provoke()` method
- Elusive wildlife can be heard but not seen
- Wildlife can have multiple traits (wolf is vicious AND skittish)
- Provocation results include health damage, fear increase, and removal from room

---

### 8. AI Interpreter (`ai_interpreter.py`)

**Responsibility:** Translates natural language input into game actions.

**Two-Tier System:**

1. **Rule-Based Fallback**: Fast, deterministic pattern matching
   - Handles common commands (inventory, look, listen, help)
   - Parses movement commands with various synonyms
   - Handles take/throw actions with flexible syntax
   - Returns `Intent` objects with action, args, confidence

2. **AI-Powered Interpretation**: LLM-based understanding
   - Uses OpenAI gpt-4o-mini
   - Understands context (room, exits, items, inventory, world flags)
   - Returns structured JSON with action, args, confidence, diegetic reply, effects
   - Enforces constraints (no inventing items/exits, small effects only)
   - Temperature=0 for consistency

**Intent Structure:**
```python
@dataclass
class Intent:
    action: str              # one of ALLOWED_ACTIONS
    args: Dict[str, str]     # e.g. {"direction": "north"}
    confidence: float        # 0.0 - 1.0
    reply: str               # diegetic one-liner for terminal
    effects: Dict[str, Any]  # {fear, health, inventory_add/remove}
    rationale: str           # debug info
```

**Allowed Actions:**
`move`, `look`, `use`, `take`, `drop`, `throw`, `listen`, `inventory`, `help`, `light`, `turn_on_lights`, `use_circuit_breaker`, `none`

**Design Notes:**
- Graceful degradation: AI → Rules → Default
- Effects are clamped to safe ranges (-2 to +2 for fear/health)
- Inventory effects validated against known items
- Direction aliases handle both cardinal directions and named locations
- All AI calls are logged for debugging
- System prompt enforces diegetic tone and constraints

---

### 9. Quest System (`quest.py`, `quests.py`)

**Responsibility:** Manages mission structure and progression.

**Quest Structure:**
```python
Quest:
  quest_id: str
  title: str
  opening_text: str          # Shown when quest activates
  objective: str             # High-level goal
  trigger_conditions: List   # What activates the quest
  update_events: Dict        # Events that provide progress updates
  completion_condition: Callable  # Check if quest is done
  completion_text: str       # Shown on completion
  quest_screen_text: str     # Shown when viewing quest (Q key)
  status: QuestStatus        # INACTIVE, ACTIVE, COMPLETED
  updates: List[QuestUpdate] # History of progress
```

**QuestManager:**
- `register_quest(quest)`: Add quest to game
- `check_triggers(trigger_type, trigger_data, player, world_state)`: Check if quest should activate
- `activate_quest(quest)`: Set quest to ACTIVE
- `check_updates(event_name, event_data, player, world_state)`: Check for progress updates
- `check_completion(player, world_state)`: Check if quest is complete
- `get_active_quest_display()`: Get text for quest screen

**Trigger Types:**
- `location`: Triggered by entering a room
- `action`: Triggered by performing an action

**Example Quest: "Warm Up"**
- **Trigger:** Multiple triggers (entering lakeside, trying to light fire, using light switch)
- **Objective:** Restore power and warmth (flip circuit breaker, gather firewood, light fire)
- **Updates:** Progress messages for gathering fuel, restoring power
- **Completion:** Both `has_power` and `fire_lit` flags are true

**Design Notes:**
- Only one active quest at a time (can be extended)
- Quests can have multiple trigger conditions
- Update events use lambda functions for flexible conditions
- Quest screen accessible via 'Q' key
- Completion checks run after successful quest actions

---

### 10. Cutscene System (`cutscene.py`)

**Responsibility:** Delivers narrative moments and set pieces.

**Cutscene Structure:**
```python
Cutscene:
  text: str                          # The cutscene content
  trigger_condition: Callable        # When to play (optional)
  has_played: bool                   # Play only once
```

**CutsceneManager:**
- `check_and_play_cutscenes(from_room_id, to_room_id, ...)`: Check and play cutscenes on movement
- `_load_cutscene_from_file(filename, trigger_condition)`: Load from markdown
- `add_cutscene(cutscene)`: Register new cutscene
- `reset_all_cutscenes()`: Allow replaying (for testing)

**Cutscene Files:**
Located in `docs/lore/cutscenes/`, written in markdown format.

**Example Trigger:**
- "entering-cabin": Plays when moving from `cabin_clearing` to `cabin_main`

**Display:**
- Clears terminal
- Shows cutscene text
- Shows separator line
- Waits for any key press
- Clears terminal again
- Resumes game

**Design Notes:**
- Cutscenes interrupt gameplay but feel integrated (no "cutscene mode")
- Loaded from external markdown files for easy content management
- Play only once per game session
- Trigger conditions are flexible callable functions

---

### 11. Requirements System (`requirements.py`)

**Responsibility:** Gates progression based on game state.

**Base Class:**
```python
class Requirement:
    def is_met(player, world_state) -> bool
    def denial_text(player, world_state) -> str  # Diegetic denial
```

**Built-in Requirements:**

1. **WorldFlagTrue**: Check if a world state flag is true
   ```python
   WorldFlagTrue("has_power", "The switch is dead. No power.")
   ```

2. **HasItem**: Check if player has a specific item
   ```python
   HasItem("key", "You pat your pockets. Empty. Not like this.")
   ```

3. **FearBelow**: Check if fear is below a threshold
   ```python
   FearBelow(60, "Your nerves spike. Your feet won't move.")
   ```

4. **CustomRequirement**: Arbitrary predicate function
   ```python
   CustomRequirement(
       lambda p, ws: p.health > 50,
       "You're too weak to continue."
   )
   ```

**Usage:**
Requirements are attached to room `exit_criteria`:
```python
room.exit_criteria = [
    WorldFlagTrue("has_power"),
    HasItem("key")
]
```

**Design Notes:**
- All denial text is diegetic (in-world)
- Requirements checked in order during movement
- Extensible via subclassing or CustomRequirement
- Can access both player state and world state

---

### 12. Logger (`logger.py`)

**Responsibility:** Debug logging and game event tracking.

**Components:**

1. **GameLogger:** Main logging class
   - File logging (always enabled)
   - Console logging (only if `CABIN_DEBUG=1`)
   - Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
   - Timestamped log files in `logs/` directory

2. **Specialized Logging Functions:**
   - `log_ai_call(user_input, context, response, error)`: Track AI interpreter calls
   - `log_quest_event(event_type, event_data)`: Track quest lifecycle
   - `log_game_action(action, args, result)`: Track game actions

**Log Files:**
- Format: `logs/the_cabin_YYYYMMDD_HHMMSS.log`
- Includes all AI interactions, quest events, game actions
- Useful for debugging input handling and AI responses

**Design Notes:**
- Silent by default (no console spam)
- Comprehensive file logging for post-game analysis
- Structured log data (dictionaries) for easy parsing
- Singleton pattern via `get_logger()`

---

## Data Flow

### 1. Input Processing Flow

```
User Input
    │
    ▼
GameEngine.handle_user_input()
    │
    ├─► "quit" → Exit game
    ├─► "q"/"quest" → Show quest screen
    ├─► "m"/"map" → Show map
    └─► Everything else
        │
        ▼
    Build context:
    - room_name
    - exits
    - room_items
    - room_wildlife
    - inventory
    - world_flags
    - allowed_actions
        │
        ▼
    ai_interpreter.interpret(user_input, context)
        │
        ├─► Try OpenAI API
        │   ├─► Success → Parse JSON Intent
        │   └─► Failure → Rule-based fallback
        │
        └─► Rule-based parsing
            ├─► Pattern match → Intent
            └─► No match → Intent(action="none")
        │
        ▼
    Return Intent:
    - action
    - args
    - confidence
    - reply (diegetic message)
    - effects (fear/health/inventory changes)
    - rationale
        │
        ▼
    GameEngine processes Intent by action type:
        │
        ├─► "move" → Map.move() + quest/cutscene checks
        ├─► "look" → Room.get_description() + items + wildlife
        ├─► "listen" → Room.get_audible_wildlife()
        ├─► "inventory" → Player.get_inventory_names()
        ├─► "take" → Room.remove_item() + Player.add_item()
        ├─► "throw" → Player.remove_item() + Wildlife.provoke()
        ├─► "use_circuit_breaker" → world_state["has_power"] = True
        ├─► "turn_on_lights" → Check world_state["has_power"]
        ├─► "light" → Check items + update world_state
        ├─► "use" → Item-specific logic
        ├─► "help" → Show help text
        └─► "none" → Fallback message
        │
        ▼
    Apply effects:
    - _apply_effects(intent)
        ├─► Update player.fear (clamped)
        ├─► Update player.health (clamped)
        ├─► Handle inventory_add (validated)
        └─► Handle inventory_remove (validated)
        │
        ▼
    Check quests:
    - _check_quest_triggers() → May activate quest
    - _check_quest_updates() → May add quest progress
    - _check_quest_completion() → May complete quest
        │
        ▼
    Set feedback:
    - self._last_feedback = message
        │
        ▼
    Next loop iteration:
    - render() displays feedback
    - wait for new input
```

### 2. Movement Flow

```
User: "go north"
    │
    ▼
AI Interpreter → Intent(action="move", args={"direction": "north"})
    │
    ▼
GameEngine.handle_user_input()
    ├─► Store current room ID (for cutscenes)
    │
    └─► Map.move("north")
        │
        ├─► Check if direction exists in room.exits
        │   └─► No → Return (False, denial message)
        │
        ├─► Check room.exit_criteria
        │   ├─► For each Requirement:
        │   │   ├─► is_met(player, world_state)?
        │   │   └─► No → Return (False, requirement.denial_text)
        │   └─► All met → Continue
        │
        ├─► Get target (location_id, room_id) from room.exits[direction]
        │
        ├─► Update current_location_id, current_room_id
        │
        ├─► Add room to visited_rooms set
        │
        └─► Call target_room.on_enter(player, world_state)
        │
        ▼
    Return (True, "")
    │
    ▼
GameEngine:
    ├─► Check quest triggers
    │
    ├─► Check cutscene triggers
    │   └─► If cutscene plays:
    │       ├─► Clear terminal
    │       ├─► Show cutscene text
    │       ├─► Wait for key press
    │       └─► Clear terminal
    │
    ├─► Apply intent effects (minimal during movement)
    │
    └─► Set _last_feedback = "" (let room description speak)
    │
    ▼
Next render():
    ├─► Detect room change
    ├─► Clear terminal
    ├─► Show room name + separator
    ├─► Show room description
    └─► Show status (health, fear)
```

### 3. Quest Lifecycle Flow

```
Game Event (e.g., player uses light switch)
    │
    ▼
GameEngine._check_quest_triggers("action", {"action": "turn_on_lights"})
    │
    ▼
QuestManager.check_triggers(trigger_type, trigger_data, player, world_state)
    │
    ├─► For each inactive quest:
    │   ├─► Check if quest.trigger_conditions match
    │   └─► If match → Return quest
    │
    └─► No match → Return None
    │
    ▼
If quest triggered:
    │
    ├─► QuestManager.activate_quest(quest)
    │   ├─► quest.status = ACTIVE
    │   └─► active_quest = quest
    │
    ├─► Log quest event
    │
    └─► Show quest screen with opening_text
        ├─► Clear terminal
        ├─► Display opening_text
        ├─► Wait for key press
        └─► Resume game

─── Player performs actions ───

GameEngine._check_quest_updates("power_restored", {...}, player, world_state)
    │
    ▼
QuestManager.check_updates(event_name, event_data, player, world_state)
    │
    ├─► If active_quest exists:
    │   ├─► Check if event_name in quest.update_events
    │   ├─► Check if trigger condition met
    │   └─► If met → Return update text
    │
    └─► No update → Return None
    │
    ▼
If update text:
    │
    ├─► quest.add_update(event_name, text, timestamp)
    │
    ├─► Log quest event
    │
    └─► Set _last_feedback = "Quest Update: {text}"

─── Player completes objectives ───

GameEngine._check_quest_completion()
    │
    ▼
QuestManager.check_completion(player, world_state)
    │
    ├─► If active_quest exists:
    │   ├─► Check quest.completion_condition(player, world_state)
    │   └─► If True:
    │       ├─► quest.status = COMPLETED
    │       ├─► quest.completed_at = now
    │       ├─► Add to completed_quests list
    │       ├─► active_quest = None
    │       └─► Return completion_text
    │
    └─► Not complete → Return None
    │
    ▼
If completion text:
    │
    ├─► Log quest event
    │
    └─► Set _last_feedback = "Quest Complete: {text}"
```

### 4. Render Cycle

```
GameEngine.render()
    │
    ├─► Get current room
    │
    ├─► Check if room changed:
    │   ├─► room.id != _last_room_id?
    │   └─► Or is first render?
    │
    └─► If room changed:
        │
        ├─► Clear terminal
        │
        ├─► Update _last_room_id
        │
        ├─► Get room description:
        │   └─► room.get_description(player, world_state)
        │       ├─► Base: static_description
        │       └─► If _description_fn exists:
        │           └─► Call _description_fn(player, world_state, base)
        │
        ├─► Print room name + separator
        │
        └─► Print description
    │
    ├─► If _last_feedback exists:
    │   ├─► Print feedback
    │   └─► Clear _last_feedback
    │
    ├─► Print status line:
    │   └─► "Health: {health}    Fear: {fear}"
    │
    └─► Print prompt:
        └─► "What would you like to do?"
    │
    ▼
Wait for input
```

---

## Separation of Concerns

### 1. Presentation Layer (GameEngine)

**Responsibilities:**
- Terminal rendering and clearing
- Input/output handling
- Screen state management (what was last shown)
- User interaction (key press waits, prompts)

**Doesn't Know About:**
- How AI interpretation works
- Room/location internals
- Quest trigger logic
- Item/wildlife behavior details

**Clean Interface:**
```python
render()         # Display current state
handle_input()   # Process user command
clear_terminal() # Platform-specific clearing
```

### 2. Game Logic Layer (Map, Player, Quest, etc.)

**Responsibilities:**
- State management (world flags, player stats, inventory)
- Game rules (movement, requirements, quest triggers)
- Content structure (rooms, items, wildlife)

**Doesn't Know About:**
- How input is interpreted
- How output is displayed
- Terminal mechanics
- API calls

**Clean Interface:**
```python
Map.move(direction) → (success, message)
Player.add_item(item) → None
Quest.check_trigger(...) → bool
Room.get_description(...) → str
```

### 3. Content Layer (Room definitions, item creation, quest definitions)

**Responsibilities:**
- Game world content (what exists)
- Narrative text
- Item/wildlife definitions
- Quest structure

**Doesn't Know About:**
- How movement works
- How rendering works
- How input is processed

**Clean Interface:**
```python
create_items() → Dict[str, Item]
create_wildlife() → Dict[str, Wildlife]
create_quest_manager() → QuestManager
```

### 4. External Services Layer (AI Interpreter)

**Responsibilities:**
- Natural language understanding
- API communication
- Fallback handling

**Doesn't Know About:**
- Game state beyond provided context
- How actions are executed
- Terminal rendering

**Clean Interface:**
```python
interpret(user_text, context) → Intent
```

### 5. Utility Layer (Logger, Requirements)

**Responsibilities:**
- Cross-cutting concerns (logging)
- Reusable patterns (requirements)

**Doesn't Know About:**
- Specific game content
- UI rendering
- Business logic

**Clean Interface:**
```python
log_ai_call(input, context, response)
Requirement.is_met(player, world_state) → bool
```

---

## Key Design Patterns

### 1. State Pattern

**Where:** Player health/fear, world_state flags, quest status

**Why:** Centralized state management makes it easy to track and modify game conditions. All systems read from and write to known state containers.

**Example:**
```python
world_state = {
    "has_power": False,
    "fire_lit": False,
    "visited_sauna": False
}
```

### 2. Strategy Pattern

**Where:** Requirements system, AI interpretation fallback

**Why:** Allows pluggable behavior without conditional logic explosion. New requirement types can be added without modifying core movement code.

**Example:**
```python
room.exit_criteria = [
    WorldFlagTrue("has_power"),
    HasItem("key"),
    FearBelow(60)
]
```

### 3. Trait/Tag Pattern

**Where:** Items, Wildlife

**Why:** Flexible behavior composition. An item can be `carryable`, `throwable`, and `weapon` without complex inheritance hierarchies.

**Example:**
```python
stone = Item(
    name="stone",
    traits={"carryable", "throwable", "weapon"}
)
```

### 4. Command Pattern

**Where:** Intent objects from AI interpreter

**Why:** Decouples input parsing from action execution. The AI interpreter produces Intent objects; the game engine executes them.

**Example:**
```python
@dataclass
class Intent:
    action: str
    args: Dict[str, str]
    confidence: float
    reply: str
    effects: Dict[str, Any]
```

### 5. Observer Pattern (Implicit)

**Where:** Quest triggers, cutscene triggers

**Why:** Game events (movement, actions) automatically check for interested observers (quests, cutscenes) without tight coupling.

**Example:**
```python
# After movement:
triggered_quest = quest_manager.check_triggers("location", {"room_id": room.id})
cutscene_played = cutscene_manager.check_and_play_cutscenes(from_room_id, to_room_id)
```

### 6. Template Method Pattern

**Where:** Room description generation, requirement checking

**Why:** Defines the skeleton of an algorithm, allowing subclasses/overrides to provide specific implementations.

**Example:**
```python
def get_description(self, player, world_state):
    base = self.static_description
    if self._description_fn is not None:
        base = self._description_fn(player, world_state, base)
    return base
```

### 7. Singleton Pattern

**Where:** Logger (`get_logger()`)

**Why:** Ensures single log file per game session, centralizes logging configuration.

**Example:**
```python
_game_logger: Optional[GameLogger] = None

def get_logger() -> GameLogger:
    global _game_logger
    if _game_logger is None:
        _game_logger = GameLogger(log_file)
    return _game_logger
```

### 8. Factory Pattern

**Where:** `create_items()`, `create_wildlife()`, `create_quest_manager()`

**Why:** Centralizes object creation, makes it easy to see all available content, allows for procedural generation.

**Example:**
```python
def create_items() -> Dict[str, Item]:
    items = {}
    items["rope"] = Item(name="rope", traits={"carryable", "usable"})
    items["matches"] = Item(name="matches", traits={"carryable", "usable"})
    return items
```

### 9. Facade Pattern

**Where:** GameEngine as facade over subsystems

**Why:** Simplifies the complex interaction between Map, Player, Quests, AI, Cutscenes into a single coherent interface.

**Example:**
```python
class GameEngine:
    def __init__(self):
        self.player = Player()
        self.map = Map()
        self.quest_manager = create_quest_manager()
        self.cutscene_manager = CutsceneManager()
        # ... etc
```

---

## Module Dependencies

### Dependency Graph

```
main.py
  └─► game_engine.py
       ├─► player.py
       ├─► map.py
       │    ├─► location.py
       │    │    └─► room.py
       │    │         └─► requirements.py
       │    ├─► room.py
       │    ├─► requirements.py
       │    ├─► item.py
       │    └─► wildlife.py
       ├─► item.py
       ├─► wildlife.py
       ├─► cutscene.py
       ├─► quests.py
       │    └─► quest.py
       ├─► logger.py
       └─► ai_interpreter.py
            └─► logger.py
```

### Dependency Principles

1. **No Circular Dependencies:** Clean one-way dependency flow
2. **Minimal Coupling:** Modules interact through well-defined interfaces
3. **Dependency Injection:** GameEngine creates and injects dependencies
4. **Interface Segregation:** Modules only know about the methods they need

### Module Relationships

**Core Domain (No External Dependencies):**
- `player.py` - Pure state container
- `item.py` - Pure data classes
- `wildlife.py` - Pure data classes with behavior
- `requirements.py` - Pure predicate objects

**World Structure (Domain Dependencies Only):**
- `room.py` ← requirements, item, wildlife
- `location.py` ← room, requirements
- `map.py` ← location, room, requirements, item, wildlife

**Game Logic (Domain + World):**
- `quest.py` - Pure quest logic
- `quests.py` ← quest (concrete quest definitions)
- `cutscene.py` - Pure cutscene logic

**External Services:**
- `ai_interpreter.py` ← logger (independent of game logic)
- `logger.py` - No dependencies

**Orchestration:**
- `game_engine.py` ← ALL modules (top-level coordinator)
- `main.py` ← game_engine

---

## Extension Points

### 1. Adding New Items

**File:** `game/item.py` → `create_items()`

**Steps:**
1. Add new item to `items` dict in `create_items()`
2. Define traits (carryable, usable, throwable, etc.)
3. Write room_description for how it appears
4. Place in room via `room.items = [items["new_item"]]` in `map.py`

**Example:**
```python
items["lantern"] = Item(
    name="lantern",
    description="An old oil lantern with a brass handle.",
    traits={"carryable", "usable"},
    room_description="A tarnished lantern hangs from a hook."
)
```

### 2. Adding New Wildlife

**File:** `game/wildlife.py` → `create_wildlife()`

**Steps:**
1. Add new wildlife to `wildlife` dict in `create_wildlife()`
2. Define traits (docile, vicious, skittish, elusive, etc.)
3. Write sound_description and visual_description
4. Add to room via `wildlife=get_random_wildlife()` or explicit list in `map.py`

**Example:**
```python
wildlife["elk"] = Wildlife(
    name="elk",
    description="A massive elk with impressive antlers.",
    traits={"docile", "massive", "skittish"},
    sound_description="Heavy hoofbeats and a deep, resonant call.",
    visual_description="An elk stands in the clearing, breath steaming."
)
```

### 3. Adding New Rooms

**File:** `game/map.py` → `Map.__init__()`

**Steps:**
1. Create new Room instance with name, description, id
2. Add items and wildlife
3. Add to appropriate Location via `location.add_room(room)`
4. Define exits in both directions (bidirectional navigation)
5. Optionally add exit_criteria

**Example:**
```python
sauna = Room(
    name="Sauna",
    description="A small log sauna, dark and cold. The stove is unlit.",
    room_id="sauna",
    items=[items["towel"], items["bucket"]],
    wildlife=[],
    max_wildlife=0
)
cabin_grounds.add_room(sauna)
sauna.exits = {"out": ("cabin_grounds", "cabin_grounds_main")}
cabin_grounds_room.exits["sauna"] = ("cabin_grounds", "sauna")
```

### 4. Adding New Locations

**File:** `game/map.py` → `Map.__init__()`

**Steps:**
1. Create new Location instance with id, name, overview
2. Add rooms to location
3. Register in `self.locations` dict
4. Connect to existing locations via room exits

**Example:**
```python
ruins = Location(
    location_id="ruins",
    name="The Ruins",
    overview_description="Ancient stone foundations, half-buried in snow."
)
old_altar = Room(
    name="Old Altar",
    description="Crumbling stone altar with strange markings.",
    room_id="old_altar"
)
ruins.add_room(old_altar)
self.locations["ruins"] = ruins
# Connect from existing room:
old_woods.exits["ruins"] = ("ruins", "old_altar")
```

### 5. Adding New Quests

**File:** `game/quests.py` → `create_quest_manager()`

**Steps:**
1. Define completion condition function
2. Define update event trigger functions
3. Create Quest instance with all parameters
4. Register with quest_manager

**Example:**
```python
def create_find_nika_quest() -> Quest:
    def completion_condition(player, world_state):
        return world_state.get("found_nika", False)
    
    return Quest(
        quest_id="find_nika",
        title="Find Nika",
        opening_text="She's out there somewhere. You have to find her.",
        objective="Search the wilderness for signs of Nika.",
        trigger_conditions=[
            {"type": "location", "room_id": "lakeside"}
        ],
        update_events={
            "found_clue": {
                "trigger": lambda ed, p, ws: ed.get("clue_type") == "nika",
                "text": "This belonged to her. She was here."
            }
        },
        completion_condition=completion_condition,
        completion_text="You found her. But it's too late.",
        quest_screen_text="Search the forest for any sign of Nika."
    )

# In create_quest_manager():
manager.register_quest(create_find_nika_quest())
```

### 6. Adding New Cutscenes

**File:** `game/cutscene.py` → `CutsceneManager._setup_cutscenes()`

**Steps:**
1. Create markdown file in `docs/lore/cutscenes/`
2. Write cutscene text with atmospheric formatting
3. Define trigger condition function
4. Load in `_setup_cutscenes()`

**Markdown File (`docs/lore/cutscenes/entering-sauna.md`):**
```markdown
# Entering the Sauna

────────────────────────────────────────────────────────────────────

You push open the sauna door.

The smell hits you first—birch, smoke, old sweat. Memory.

She loved this place. Even in winter. Especially in winter.

"It's not about the heat," she'd say. "It's about the reset."

The bucket still hangs from its hook, wooden ladle across the rim.

You touch the stove. Cold iron. Dead for months.

────────────────────────────────────────────────────────────────────
```

**Trigger Function:**
```python
def _sauna_entry_trigger(self, from_room_id: str, to_room_id: str, **kwargs) -> bool:
    return to_room_id == "sauna"

# In _setup_cutscenes():
self._load_cutscene_from_file("entering-sauna", self._sauna_entry_trigger)
```

### 7. Adding New Requirements

**File:** `game/requirements.py`

**Steps:**
1. Create new class inheriting from `Requirement`
2. Implement `is_met(player, world_state)` method
3. Implement `denial_text(player, world_state)` method
4. Use in room exit_criteria

**Example:**
```python
class HealthAbove(Requirement):
    def __init__(self, threshold: int, message: Optional[str] = None):
        self.threshold = threshold
        self._message = message
    
    def is_met(self, player, world_state) -> bool:
        return getattr(player, "health", 100) > self.threshold
    
    def denial_text(self, player, world_state) -> str:
        if self._message:
            return self._message
        return "You're too injured. Your body won't cooperate."

# Usage in map.py:
dangerous_room.exit_criteria = [HealthAbove(50)]
```

### 8. Adding New Actions

**File:** `game/ai_interpreter.py` → `ALLOWED_ACTIONS`

**Steps:**
1. Add action name to `ALLOWED_ACTIONS` set
2. Update system prompt to explain the action
3. Add handling in `GameEngine.handle_user_input()`
4. Optionally add rule-based pattern matching

**Example:**
```python
# In ai_interpreter.py:
ALLOWED_ACTIONS = {..., "sleep", ...}

# In system prompt:
"- Use 'sleep' for resting to recover health."

# In game_engine.py handle_user_input():
elif intent.action == "sleep":
    self._apply_effects(intent)
    if self._is_safe_location():
        self.player.health = min(100, self.player.health + 20)
        self.player.fear = max(0, self.player.fear - 10)
        self._last_feedback = intent.reply or "You close your eyes. The dreams are worse than the waking."
    else:
        self._last_feedback = intent.reply or "You can't rest here. Something's watching."
```

### 9. Procedural Room Descriptions

**File:** Room definition in `map.py`

**Steps:**
1. Define a function that takes (player, world_state, base_text) and returns modified text
2. Pass as `description_fn` parameter to Room constructor

**Example:**
```python
def cabin_interior_description(player, world_state, base_text):
    desc = base_text
    
    if world_state.get("has_power", False):
        desc += "\n\nWarm light fills the room from overhead bulbs."
    else:
        desc += "\n\nThe cabin is dark, lit only by what little daylight filters through."
    
    if world_state.get("fire_lit", False):
        desc += " The fireplace crackles softly, throwing dancing shadows."
    
    if player.fear > 70:
        desc += "\n\nThe corners seem to move when you're not looking directly at them."
    
    return desc

cabin = Room(
    name="The Cabin",
    description="You are inside a small cabin...",
    room_id="cabin_main",
    description_fn=cabin_interior_description
)
```

### 10. Custom World State

**File:** `game/map.py` → `Map.__init__()`

**Steps:**
1. Add new keys to `self.world_state` dictionary
2. Modify state in appropriate action handlers in `game_engine.py`
3. Reference in requirements, quest conditions, or room descriptions

**Example:**
```python
# In map.py __init__:
self.world_state = {
    "has_power": False,
    "fire_lit": False,
    "sauna_heated": False,
    "found_journal": False,
    "time_of_day": "evening"
}

# In game_engine.py:
elif intent.action == "heat_sauna":
    if world_state.get("has_power", False) and player.has_item("firewood"):
        world_state["sauna_heated"] = True
        self._last_feedback = "The sauna stove roars to life. Soon it will be warm."
    else:
        self._last_feedback = "You need power and fuel to heat the sauna."
```

---

## State Management

### 1. Player State

**Location:** `player.py` → `Player` class

**State Variables:**
- `name`: str - Character name
- `health`: int (0-100) - Physical condition
- `fear`: int (0-100) - Mental state
- `inventory`: List[Item] - Carried items

**State Transitions:**
- Health/fear modified by action effects, wildlife attacks, environmental conditions
- Inventory modified by take/drop/throw actions
- State is mutable and modified in-place

**Persistence:** Not implemented (future extension point)

### 2. World State

**Location:** `map.py` → `Map.world_state`

**State Variables:**
- Dictionary of string keys to object values
- Typical flags: "has_power", "fire_lit", etc.
- Can store booleans, numbers, strings, or complex objects

**State Transitions:**
- Modified by action handlers in `game_engine.py`
- Read by requirements, quest conditions, room descriptions
- Global state accessible to all systems

**Persistence:** Not implemented (future extension point)

### 3. Room State

**Location:** `room.py` → `Room` instances

**State Variables:**
- `items`: List[Item] - Items currently in room
- `wildlife`: List[Wildlife] - Wildlife currently in room

**State Transitions:**
- Items added/removed by take/drop actions
- Wildlife added/removed by provoke actions or procedural generation
- State is mutable and modified in-place

**Persistence:** Not implemented (items/wildlife reset on game restart)

### 4. Quest State

**Location:** `quest.py` → `Quest` instances

**State Variables:**
- `status`: QuestStatus - INACTIVE, ACTIVE, COMPLETED
- `updates`: List[QuestUpdate] - Progress history
- `completed_at`: Optional[float] - Timestamp of completion

**State Transitions:**
- INACTIVE → ACTIVE: Trigger condition met
- ACTIVE → COMPLETED: Completion condition met
- Updates added during ACTIVE state

**Persistence:** Not implemented (quest progress resets)

### 5. Cutscene State

**Location:** `cutscene.py` → `Cutscene` instances

**State Variables:**
- `has_played`: bool - Track if cutscene has been shown

**State Transitions:**
- False → True: After cutscene plays

**Persistence:** Not implemented (cutscenes replay on game restart)

### 6. Map State

**Location:** `map.py` → `Map` instance

**State Variables:**
- `current_location_id`: str - Current location
- `current_room_id`: str - Current room
- `visited_rooms`: Set[str] - Rooms player has entered

**State Transitions:**
- Modified by movement (Map.move())
- Used for map visualization and tracking exploration

**Persistence:** Not implemented (exploration resets)

### 7. UI State

**Location:** `game_engine.py` → `GameEngine` instance

**State Variables:**
- `_last_feedback`: str - Message to display once
- `_last_room_id`: str - Track room changes
- `_is_first_render`: bool - Track first render

**State Transitions:**
- Modified by action handlers
- Cleared after display in render()

**Persistence:** Not applicable (UI state is transient)

---

## Conclusion

**The Cabin** demonstrates a clean separation of concerns with:

1. **Modular Architecture:** Each module has a clear, singular responsibility
2. **Extensible Design:** New content and features can be added without modifying core systems
3. **Diegetic Philosophy:** All game systems serve the atmospheric, in-world experience
4. **AI Integration:** Seamless natural language understanding with rule-based fallbacks
5. **State Management:** Clear, centralized state with well-defined modification points

The architecture prioritizes:
- **Maintainability:** Clean interfaces and minimal coupling
- **Extensibility:** Multiple extension points for content and features
- **Testability:** Pure functions and clear dependencies
- **Atmosphere:** Technical design serves narrative goals

This foundation supports current gameplay while providing clear paths for future expansion, including persistence, additional mechanics, and web interface development.

---

**Document Maintenance:**

This architecture document should be updated when:
- New major systems are added (e.g., save/load, weather system)
- Core patterns change (e.g., moving to ECS architecture)
- Module responsibilities shift significantly
- New extension points are created

For questions or clarifications about the architecture, refer to inline code comments and docstrings in the source files.

