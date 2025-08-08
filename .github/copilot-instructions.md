# The Cabin - AI Coding Instructions

This is a survival horror text adventure game in Python, featuring atmospheric storytelling with supernatural elements.

## Architecture Overview

- **Entry Point:** `main.py` → `GameEngine` → game loop with Rich-based UI
- **Core Components:**
  - `game/game_engine.py` - Main game loop, input handling, terminal management
  - `game/map.py` - Room network and navigation (hardcoded room connections)
  - `game/player.py` - Player state (health=100, fear=0, inventory, name="Eli")
  - `game/game_ui.py` - Rich-based UI with 3-panel layout (status/main/input)
  - `game/room.py` - Simple room class (name, description, exits dict)

## Game Design Philosophy

**Tone:** Creeping dread, Finnish wilderness setting, grounded realism (not power fantasy)
**Core Mechanic:** Health/Fear dual-stat system where high fear affects action success
**The Lyer:** Central antagonist - ancient, patient entity that "lies in wait" (never directly described)

## Key Patterns & Conventions

### UI Architecture
```python
# Rich Layout Pattern - 3-panel split
layout.split(Layout("top", size=4), Layout("main", ratio=1), Layout("input", size=3))
```

### Room Navigation
```python
# Exits are dictional references to Room objects
room.exits = {"north": another_room, "cabin": cabin_room}
# Movement: tokens[0] == "go" and tokens[1] in current_room.exits
```

### Content Structure
- `content/lore/` - In-universe worldbuilding and narrative elements
- `content/game_mechanics/` - Out-of-universe rules and system specs
- `content/game_mechanics/diegetic_action_interpretor.md` - AI behavior rules for parsing player input

## Development Workflows

**Run Game:** `python main.py` (uses Rich for terminal UI, requires clearing terminal)
**Dependencies:** Rich library for UI components (no requirements.txt yet)
**Python Environment:** Uses conda/base environment

## Critical Implementation Notes

### Diegetic Design Principle
All AI responses must be **in-world** - never break the fourth wall or mention game systems directly. Use second-person present tense with sensory details.

### Input Parsing Strategy
Currently basic "go direction" parsing, but designed for hybrid system:
- Suggested actions (2-4 options)
- Free-text input with intent parsing
- Graceful handling of typos and synonyms

### Fear/Health Mechanics
- Fear affects action success rates (fumbling, misreading, etc.)
- Health affects mobility and perception
- Both recovered through specific in-world actions (rest, light, warmth)

### The Lyer Rules
- Cannot be directly confronted early-game (instant death)
- Presence causes maximum fear spike
- Influence is primarily emotional/atmospheric
- Name itself is unsettling when spoken

## TODO Items
- Integrate AI prompts for dynamic content generation
- Implement room progression criteria (player advances when specific conditions met)
- Add proper dependency management (requirements.txt/pyproject.toml)
