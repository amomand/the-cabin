# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

The Cabin is a survival horror text adventure (Python 3.10+) with AI-powered natural language input. Set in the Finnish wilderness, it uses OpenAI's GPT for diegetic (in-world) responses. The game never breaks the fourth wall — there is no "invalid command", only narrated in-world outcomes.

## Commands

```bash
# Run the game
python main.py

# Run the game with debug output
CABIN_DEBUG=1 python main.py

# Run all tests (231 tests)
python -m pytest

# Run tests with coverage
python -m pytest --cov=game --cov-report=term-missing

# Run a specific test file
python -m pytest tests/actions/test_move.py -v

# Run a specific test module
python -m pytest tests/actions -v
```

Requires `OPENAI_API_KEY` in `.env` to run the game (not needed for tests).

## Architecture

**Data flow:** User Input → InputHandler → CommandParser (trivial) / AI Interpreter (creative) → ActionRegistry → EffectManager → EventBus → RenderManager

**Key modules under `game/`:**

- `game_engine.py` — Main orchestrator. Coordinates the full loop: render → input → AI → action → effects → events → render.
- `ai_interpreter.py` — GPT integration. Parses free-text input into `Intent(action, args, confidence, reply, effects)`. Has LRU response cache (50 entries). Falls back to rule-based parsing for trivial commands.
- `actions/` — 13 action classes implementing `Action` ABC (`base.py`). Each has `execute(ctx: ActionContext) -> ActionResult`. Dispatched by `ActionRegistry` (`registry.py`). Registered in `__init__.py` via `create_default_registry()`.
- `events/` — Pub/sub `EventBus` (`bus.py`). Actions emit events, listeners in `events/listeners/` handle quest progression and cutscenes.
- `input/` — `InputHandler` routes system commands (quit/save/load). `CommandParser` handles trivial commands (movement, inventory, look) to avoid AI API calls. Everything else goes to AI.
- `effects/manager.py` — Applies fear/health/inventory changes from action results.
- `render/` — `RenderManager` displays rooms and feedback. `TerminalAdapter` abstracts terminal I/O.
- `persistence/save_manager.py` — JSON-based save/load in `saves/` directory.
- `game_state.py` — Unified state container for serialization. `world_state.py` has typed flags (`has_power`, `fire_lit`) plus dict-like access for custom flags.
- `config.py` — Loads from env vars (precedence) and `config.json`. Access via `get_config()`.

**Dependency injection:** All major components accept dependencies via constructors, enabling unit testing without mocks. Test fixtures are in `tests/conftest.py`.

## Extending the Game

**New action:** Create class in `game/actions/` implementing `Action` ABC → register in `game/actions/__init__.py` → add to `ALLOWED_ACTIONS` in `ai_interpreter.py` → write tests in `tests/actions/`.

**New event:** Define in `game/events/types.py` → emit from action's `ActionResult.events` → handle in `game_engine.py` `_handle_action_events()` → subscribe listener if needed.

**New quest:** Add to `game/quests.py` → subscribe listener to events in `game/events/listeners/`.

**New room:** Add to a location in `game/map.py`.

## Diegetic Immersion (Critical Design Constraint)

All player-facing text must stay in-world. Fourth-wall breaks are bugs.

- Voice: second person, present tense, sensory, terse (1-3 sentences), bleak
- Impossible actions get narrated failures with consequences (fear/health), never "you can't do that"
- The CommandParser has narrow scope — only trivially obvious commands. When in doubt, return `UNKNOWN` and let the AI handle it
- The Lyer (the antagonist) is implied, never explained, never trivialized
- Anti-patterns: "Invalid command", "You can't do that here", "Error:", third-person narration, explaining game mechanics
