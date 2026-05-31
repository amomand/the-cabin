# The Cabin - Architecture

**Version:** 2.0 | **Updated:** January 2026

A survival horror text adventure with AI-powered natural language input.

---

## Core Principle: Diegetic Immersion

**The AI is the core experience, not a fallback.**

- The game NEVER breaks the fourth wall
- "You can't do that" must NEVER appear
- Impossible actions → narrated failure with consequences
- All responses in second-person, present tense

```
❌ "Invalid command"
✅ "You tense your legs, willing yourself upward. Gravity wins."
```

---

## Architecture Overview

```
main.py
    │
    ▼
┌─────────────────────────────────────────────────────┐
│                    GameEngine                        │
│       Canonical terminal orchestration path          │
└──────┬────────┬────────┬────────┬────────┬─────────┘
       │        │        │        │        │
       ▼        ▼        ▼        ▼        ▼
   Actions   Events   Render   Input   Persist
   Registry    Bus   Methods  Handler   Save
       │        │
       ▼        ▼
   15 Action  Quest &
   Classes   Cutscene
             Listeners
```

---

## Directory Structure

```
game/
├── game_engine.py      # Main orchestrator
├── game_state.py       # Unified state container
├── world_state.py      # Typed world flags
├── config.py           # Configuration loader
├── ai_interpreter.py   # GPT-5.4-mini integration
│
├── actions/            # 15 action classes (move, look, take, accept/refuse, etc.)
├── events/             # EventBus + listeners
├── input/              # InputHandler + legacy CommandParser helpers
├── persistence/        # SaveManager (JSON saves)
│
├── player.py, map.py, room.py, item.py, wildlife.py
├── quest.py, quests.py, cutscene.py, requirements.py
└── logger.py
```

---

## Key Components

### GameEngine
Main orchestrator. Coordinates: render → input → AI → action → effects → events.

### ActionRegistry
Maps action names to classes. 15 actions: `move`, `look`, `listen`, `take`, `drop`, `inventory`, `throw`, `use`, `light`, `help`, Act V `accept`/`refuse`, etc.

### EventBus
Pub/sub system. Actions emit events → Listeners handle quests/cutscenes.

### AI Interpreter
- Uses `gpt-5.4-mini` by default (configurable)
- Response caching (LRU, 50 entries)
- Rule-based handling inside `interpret()` for common commands and Act V physical threshold choices

### SaveManager
JSON saves in `saves/` directory. Persists player, map, world state, quests.

---

## Data Flow

```
User Input
    │
    ▼
InputHandler ──→ quit/save/load/quest/map (system commands)
    │
    ▼
AI Interpreter ──→ rule-based obvious commands or model interpretation
                   Intent (action, args, reply, effects)
    │
    ▼
ActionRegistry.execute() ──→ ActionResult
    │
    ▼
GameEngine._apply_effects() ──→ apply fear/health/inventory
    │
    ▼
EventBus.emit() ──→ quest triggers, cutscenes
    │
    ▼
GameEngine.render() ──→ display room + feedback
```

---

## World Structure

```
Map
 ├── WorldState (has_power, fire_lit, custom flags)
 ├── Locations
 │    └── Rooms (description, items, wildlife, exits)
 └── visited_rooms, current_room
```

---

## Configuration

Environment variables (take precedence):
- `OPENAI_API_KEY` - Required
- `OPENAI_MODEL` - Default: gpt-5.4-mini
- `CABIN_DEBUG=1` - Enable debug output

Or `config.json`:
```json
{
  "openai_model": "gpt-5.4-mini",
  "debug_mode": false,
  "max_log_files": 10
}
```

---

## Testing

```bash
python -m pytest              # Full suite
python -m pytest --cov=game --cov=server   # With coverage
```

---

## Extension Points

1. **New Action**: Add class in `game/actions/`, register in `__init__.py`
2. **New Event**: Add to `game/events/types.py`, emit from action
3. **New Quest**: Add to `game/quests.py`, subscribe listener to events
4. **New Room**: Add to location in `game/map.py`

See `developer-guide.md` for detailed instructions.

---

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| AI for creative input | Core differentiator - diegetic responses |
| Rule parser for trivials | Reduce API costs for obvious commands |
| Event-driven quests | Decouple quest logic from actions |
| JSON saves | Human-readable, easy debugging |
| Dependency injection | Testability without mocks |

---

## Files by Purpose

| Purpose | Files |
|---------|-------|
| Entry | `main.py` |
| Orchestration | `game_engine.py` |
| State | `game_state.py`, `world_state.py`, `player.py` |
| World | `map.py`, `room.py`, `location.py` |
| Content | `item.py`, `wildlife.py`, `quests.py`, `cutscene.py` |
| AI | `ai_interpreter.py` |
| Actions | `actions/*.py` |
| Events | `events/*.py` |
| I/O | `input/*.py`, `game_engine.py` terminal render helpers |
| Persistence | `persistence/*.py` |
| Config | `config.py`, `logger.py` |
