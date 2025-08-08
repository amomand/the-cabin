# The Cabin - AI Coding Instructions

This file provides context and architectural guidance to AI coding assistants (like GitHub Copilot) working within this codebase. It ensures generated code aligns with the game's tone, mechanics, and structural conventions.

AI agents assisting in this project should:
- Follow the diegetic principle (see below).
- Respect existing architecture and file boundaries.
- Generate code that aligns with tone, mechanics, and gameplay structure.
- Avoid introducing new frameworks or systems unless explicitly requested.

## 🧠 AI Coding Guidelines

This is a survival horror text adventure game in Python, featuring atmospheric storytelling with supernatural elements.

## 🗺️ Game Architecture

- **Entry Point:** `main.py` → `GameEngine` → game loop with Rich-based UI
- **Core Components:**
  - `game/game_engine.py` - Main game loop, input handling, terminal management
  - `game/map.py` - Room network and navigation (hardcoded room connections)
  - `game/player.py` - Player state (health=100, fear=0, inventory, name="Eli")
  - `game/game_ui.py` - Rich-based UI with 3-panel layout (status/main/input)
  - `game/room.py` - Simple room class (name, description, exits dict)

## 📁 Directory Overview
- `game/` — core game logic
- `content/lore/` — in-universe worldbuilding
- `content/game_mechanics/` — out-of-universe rules
- `content/game_mechanics/diegetic_action_interpretor.md` — AI behavior logic

## 🎮 Game Design Philosophy

**Tone:** Creeping dread, Finnish wilderness setting, grounded realism (not power fantasy)
**Core Mechanic:** Health/Fear dual-stat system where high fear affects action success
**The Lyer:** Central antagonist - ancient, patient entity that "lies in wait" (never directly described)

## 🧩 Key Mechanics & Systems

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

## 🛠️ Dev Environment & Workflows

**Run Game:** `python main.py` (uses Rich for terminal UI, requires clearing terminal)
**Dependencies:** Rich library for UI components (no requirements.txt yet)
**Python Environment:** Uses conda/base environment

## Critical Implementation Notes

### Diegetic Design Principle
All AI responses must be **in-world** - never break the fourth wall or mention game systems directly. Use second-person present tense with sensory details.

### Diegetic AI Response Examples

✅ “You lift the rock and toss it into the trees. It vanishes into the gloom with a soft rustle.”

❌ “That’s not a valid action. Try again!”

❌ “As an AI, I can’t do that.”

### Input Parsing Strategy
Currently basic "go direction" parsing, but designed for hybrid system:
- Suggested actions (2-4 options)
- Free-text input with intent parsing
- Graceful handling of typos and synonyms

### Fear/Health Mechanics
- Fear affects action success rates (fumbling, misreading, etc.)
- Health affects mobility and perception
- Both recovered through specific in-world actions (rest, light, warmth)

### Player Model Summary
- Name: Eli (default)
- Health: Integer (0–100)
- Fear: Integer (0–100) — higher values reduce success chance
- Inventory: List of item objects
- State affected by light, warmth, rest

### The Lyer Rules
- Cannot be directly confronted early-game (instant death)
- Presence causes maximum fear spike
- Influence is primarily emotional/atmospheric
- Name itself is unsettling when spoken

## ✨ AI-Generated Content Notes
Certain elements (e.g. room descriptions, events) may be procedurally generated via AI prompt pipelines. These must:
- Stay within tone
- Avoid breaking game logic
- Be templated or sandboxed for consistency

## 🚧 TODOs & Next Steps
- Integrate AI prompts for dynamic content generation
- Implement room progression criteria (player advances when specific conditions met)
- Add proper dependency management (requirements.txt/pyproject.toml)
