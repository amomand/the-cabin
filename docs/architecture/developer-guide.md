# Developer Guide - The Cabin

**Last Updated:** January 29, 2026

This guide covers the refactored architecture and how to extend The Cabin.

---

## Architecture Overview

After the Phase 1-5 refactoring, the codebase follows a modular, testable design:

```
main.py                         # Entry point
game/
├── game_engine.py              # Main orchestrator (backward compatible)
├── game_loop.py                # Thin orchestrator (<160 lines)
├── game_state.py               # Unified state container
├── world_state.py              # Typed world flags
├── config.py                   # Configuration loader
│
├── actions/                    # Action implementations
│   ├── base.py                 # Action ABC, ActionResult, ActionContext
│   ├── registry.py             # Action dispatch
│   ├── move.py, observe.py, inventory.py, throw.py, use.py, light.py, help.py
│
├── events/                     # Event system
│   ├── bus.py                  # Pub/sub EventBus
│   ├── types.py                # Typed GameEvent classes
│   └── listeners/              # Quest, cutscene listeners
│
├── input/                      # Input processing
│   ├── handler.py              # Input routing (quit, save, load, etc.)
│   └── command_parser.py       # Rule-based parsing for trivial commands
│
├── render/                     # Display
│   ├── manager.py              # RenderManager
│   └── terminal.py             # Terminal abstraction
│
├── effects/                    # State changes
│   └── manager.py              # Apply fear/health/inventory
│
├── persistence/                # Save/load
│   └── save_manager.py         # JSON-based saves
│
└── ai_interpreter.py           # AI-powered command interpretation
```

---

## Key Design Principles

### 1. Diegetic AI Philosophy (CRITICAL)

The AI is NOT a fallback — it's the core experience.

**Rules:**
- The game NEVER breaks the fourth wall
- "You can't do that" must NEVER appear
- Impossible actions → narrated failure WITH consequences
- AI handles anything creative, ambiguous, or roleplay-like

**Examples:**
```
❌ "Invalid command"
❌ "You can't do that here"
✅ "You tense your legs, willing yourself upward. Gravity wins."
✅ "A sneeze tears through you. Something in the trees goes quiet."
```

See: `docs/game_mechanics/diegetic_action_interpretor.md`

### 2. Command Parser (Narrow Scope)

`CommandParser` handles ONLY trivially obvious commands:
- Movement: "go north", "n", "north"
- Inventory: "i", "take rope", "drop stick"  
- Observation: "look", "listen"
- System: "quit", "save", "load", "help"

**Everything else goes to AI.** When in doubt, return `UNKNOWN`.

### 3. Dependency Injection

All major components accept dependencies through constructors:

```python
engine = GameEngine(
    player=mock_player,
    map=mock_map,
    event_bus=mock_bus,
    action_registry=mock_registry,
)
```

This enables isolated unit testing without mocking.

---

## Adding a New Action

1. **Create the action class** in `game/actions/`:

```python
# game/actions/examine.py
from game.actions.base import Action, ActionResult, ActionContext

class ExamineAction(Action):
    def execute(self, ctx: ActionContext) -> ActionResult:
        target = ctx.args.get("target", "")
        
        # Check if target exists in room
        room = ctx.map.current_room
        if target in [item.name for item in room.items]:
            description = f"You examine the {target} closely..."
            return ActionResult(success=True, feedback=description)
        
        return ActionResult(
            success=False,
            feedback=f"There's no {target} here to examine."
        )
```

2. **Register in the registry** (`game/actions/__init__.py`):

```python
from game.actions.examine import ExamineAction

def create_default_registry() -> ActionRegistry:
    registry = ActionRegistry()
    # ... existing actions ...
    registry.register("examine", ExamineAction())
    return registry
```

3. **Update AI interpreter** (`game/ai_interpreter.py`):
   - Add "examine" to `ALLOWED_ACTIONS`
   - Update system prompt to describe when to use it

4. **Write tests** (`tests/actions/test_examine.py`)

---

## Adding a New Event

1. **Define the event type** in `game/events/types.py`:

```python
@dataclass
class ExamineEvent(GameEvent):
    item_name: str
    room_id: str
```

2. **Emit from the action** in the action's `execute()` method:

```python
return ActionResult(
    success=True,
    feedback="...",
    events=["item_examined"],
    state_changes={"item_name": target}
)
```

3. **Handle in GameEngine** (`_handle_action_events()`):

```python
elif event_name == "item_examined":
    item_name = state_changes.get("item_name", "")
    self.event_bus.emit(ExamineEvent(
        item_name=item_name,
        room_id=self.map.current_room.id
    ))
```

4. **Subscribe a listener** if needed (e.g., quest progression).

---

## Configuration

Configuration is loaded from environment variables and `config.json`:

```python
from game.config import get_config

config = get_config()
print(config.debug_mode)
print(config.max_log_files)
```

Environment variables take precedence:
- `OPENAI_API_KEY` - API key
- `CABIN_DEBUG=1` - Enable debug output
- `CABIN_SAVE_DIR` - Save directory
- `CABIN_LOG_DIR` - Log directory
- `CABIN_MAX_LOGS` - Max log files to keep

---

## Testing

Run all tests:
```bash
python -m pytest
```

Run with coverage:
```bash
python -m pytest --cov=game --cov-report=term-missing
```

Run specific test file:
```bash
python -m pytest tests/actions/test_move.py -v
```

**Test fixtures** are in `tests/conftest.py`:
- `player` - Fresh Player instance
- `world_state` - Fresh WorldState
- `room` - Mock room with items/exits

---

## Save/Load System

Saves are JSON files in `saves/` directory:

```python
from game.persistence import SaveManager

manager = SaveManager()
manager.save_game(game_state, "slot1")
data = manager.load_game("slot1")
```

Save file structure:
```json
{
  "version": 1,
  "timestamp": "2026-01-29T12:00:00",
  "slot_name": "slot1",
  "game_state": {
    "player": { "health": 100, "fear": 10, "inventory": ["rope"] },
    "map": { "current_room_id": "cabin", "visited_rooms": [...] },
    "world_state": { "has_power": true, "fire_lit": false },
    "quests": { "active_quest_id": "q1", "completed_quests": [] }
  }
}
```

---

## Logging

Logs are written to `logs/` directory with automatic rotation (keeps last 10):

```python
from game.logger import get_logger, log_ai_call

logger = get_logger()
logger.info("Something happened")
logger.debug("Debug detail")

# Log AI calls
log_ai_call(user_input, context, response_dict)
```

Enable debug mode: `CABIN_DEBUG=1 python main.py`

---

## Response Caching

AI responses are cached to reduce API calls:

```python
from game.ai_interpreter import clear_response_cache

# Cache is automatically invalidated on context change
# Manually clear if needed:
clear_response_cache()
```

Cache key includes: user_text, room_name, exits, room_items, inventory, world_flags

---

## Common Patterns

### Action returning events:
```python
return ActionResult(
    success=True,
    feedback="You pick up the rope.",
    events=["item_taken", "fuel_gathered"],
    state_changes={"item_name": "rope"}
)
```

### Checking world state:
```python
if ctx.map.world_state.has_power:
    # Power is on
if ctx.map.world_state["custom_flag"]:
    # Custom flag is set
```

### Modifying player state:
```python
ctx.player.fear = min(100, ctx.player.fear + 10)
ctx.player.add_item(item)
```

---

## Test Coverage Goals

| Component | Target |
|-----------|--------|
| Actions | 90%+ |
| Events | 90%+ |
| Input | 85%+ |
| Persistence | 85%+ |
| Overall | 80%+ |

Current: 231 tests passing
