# The Cabin - Re-Architecture Plan

**Created:** January 29, 2026  
**Status:** Planning

---

## Executive Summary

This plan restructures The Cabin codebase from a monolithic GameEngine design to a modular, testable architecture. The goal is to enable:
- Unit testing of individual components
- Easy addition of new actions/content without modifying core systems
- Fast handling of trivial commands (movement, inventory) without API calls
- **Preserved diegetic AI experience** for creative/impossible input (the core differentiator)
- Save/load functionality
- Type-safe state management

**Key Design Principle:** The AI interpreter is NOT a fallback — it's the core experience. The rule-based parser only handles trivially obvious commands. Anything creative, ambiguous, or impossible MUST go to the AI for an in-character, consequence-driven response. "You can't do that" should NEVER appear.

**Estimated Total Effort:** 6-8 weeks  
**Phases:** 5

---

## Current State Summary

| Metric | Current | Target |
|--------|---------|--------|
| GameEngine lines | 535 | <200 |
| Test coverage | 0% | 80%+ |
| Type coverage | ~60% | 100% |
| Trivial commands offline | ~15% | 100% |
| Creative input → diegetic AI | partial | always |
| Save/Load | None | Full |

### Critical Issues to Address

1. **God Object** — GameEngine handles input, rendering, actions, quests, effects, state
2. **No Tests** — Zero test files, no safety net for refactoring
3. **No DI** — All dependencies created inline, untestable
4. **Primitive State** — `Dict[str, object]` world state with no validation
5. **Duplicate Creation** — Items/wildlife created in both GameEngine and Map
6. **Ad-hoc Quest Integration** — Some actions trigger quests, others don't
7. **Scattered Content** — Room/item/quest definitions spread across files
8. **Heavy API Dependency** — Poor offline experience for trivial commands

---

## Target Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                          main.py                                 │
│                      (Entry Point)                               │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                        GameLoop                                  │
│  • Coordinates render → input → execute → effects cycle          │
│  • Delegates ALL work to injected components                     │
│  • Under 100 lines                                               │
└──┬──────────┬──────────┬──────────┬──────────┬─────────────────┘
   │          │          │          │          │
   ▼          ▼          ▼          ▼          ▼
┌──────┐ ┌────────┐ ┌─────────┐ ┌────────┐ ┌─────────┐
│Render││ Input  ││ Action  ││ Effect ││  Event  │
│Mgr   ││ Handler││ Executor││ Manager││  Bus    │
└──────┘ └────────┘ └────┬────┘ └────────┘ └────┬────┘
                         │                      │
                         ▼                      ▼
                  ┌─────────────┐        ┌─────────────┐
                  │   Actions   │        │  Listeners  │
                  │ (Registry)  │        │ Quest/etc   │
                  └─────────────┘        └─────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                        GameState                                 │
│  • Player (health, fear, inventory)                              │
│  • WorldState (typed flags)                                      │
│  • MapState (current room, visited)                              │
│  • QuestState (active, completed)                                │
└─────────────────────────────────────────────────────────────────┘
```

---

## Phase 1: Foundation (Week 1-2)

**Goal:** Enable testing and dependency injection without changing behavior.

### Tasks

- [ ] **1.1 Add pytest infrastructure**
  - Create `tests/` directory structure
  - Add `pytest.ini` and `conftest.py`
  - Add pytest to requirements.txt
  - Create first smoke test that imports all modules

- [ ] **1.2 Create GameState container**
  - New file: `game/game_state.py`
  - Dataclass containing: player, world_state, map_state, quest_state
  - Add `to_dict()` and `from_dict()` for future serialization
  - Keep backward compatibility with current code

- [ ] **1.3 Create typed WorldState**
  - New file: `game/world_state.py`
  - Dataclass with explicit flags: `has_power`, `fire_lit`, etc.
  - Validation method
  - Migrate `Map.world_state` dict to use this class
  - Add compatibility property for dict-style access during transition

- [ ] **1.4 Fix duplicate item/wildlife creation**
  - Remove `self.items` and `self.wildlife` from GameEngine
  - Add property accessors that delegate to Map
  - Verify no behavior change

- [ ] **1.5 Add dependency injection to GameEngine**
  - Constructor accepts optional dependencies
  - Default to creating them if not provided
  - Enables injecting mocks for testing

- [ ] **1.6 Write tests for core domain objects**
  - `test_player.py` — inventory operations, health/fear clamping
  - `test_item.py` — trait checking
  - `test_wildlife.py` — provoke behavior
  - `test_requirements.py` — requirement evaluation
  - Target: 40% coverage

### Deliverables
- Working test suite with pytest
- Typed WorldState with validation
- GameState container
- Dependency injection enabled
- No duplicate object creation
- 40%+ test coverage on domain objects

### Files Created/Modified
```
game/
  game_state.py      (new)
  world_state.py     (new)
  game_engine.py     (modified - DI, remove duplicates)
  map.py             (modified - use WorldState)
tests/
  __init__.py        (new)
  conftest.py        (new)
  test_player.py     (new)
  test_item.py       (new)
  test_wildlife.py   (new)
  test_requirements.py (new)
  test_world_state.py  (new)
pytest.ini           (new)
requirements.txt     (modified - add pytest)
```

---

## Phase 2: Extract Actions (Week 2-3)

**Goal:** Move action logic out of GameEngine into testable Action classes.

### Tasks

- [ ] **2.1 Create Action base class and ActionResult**
  - New file: `game/actions/base.py`
  - Abstract `Action` class with `execute(game_state, intent) -> ActionResult`
  - `ActionResult` dataclass: success, feedback, state_changes, events

- [ ] **2.2 Create ActionRegistry**
  - New file: `game/actions/registry.py`
  - Maps action names to Action instances
  - `execute(action_name, game_state, intent)` method

- [ ] **2.3 Extract MoveAction**
  - New file: `game/actions/move.py`
  - Move all movement logic from GameEngine
  - Return events: `["player_moved", "entered_room"]`
  - Write tests

- [ ] **2.4 Extract LookAction and ListenAction**
  - New file: `game/actions/observe.py`
  - Move look/listen logic
  - Write tests

- [ ] **2.5 Extract InventoryAction (take, drop, inventory)**
  - New file: `game/actions/inventory.py`
  - Move take/drop/inventory logic
  - Return events: `["item_taken", "item_dropped"]`
  - Write tests

- [ ] **2.6 Extract ThrowAction**
  - New file: `game/actions/throw.py`
  - Move throw logic including wildlife interaction
  - Return events: `["item_thrown", "wildlife_provoked"]`
  - Write tests

- [ ] **2.7 Extract UseAction**
  - New file: `game/actions/use.py`
  - Move use logic (circuit breaker, matches, etc.)
  - Return events: `["item_used", "power_restored", "fire_lit"]`
  - Write tests

- [ ] **2.8 Extract LightAction**
  - New file: `game/actions/light.py`
  - Move fire-lighting logic
  - Write tests

- [ ] **2.9 Integrate ActionRegistry into GameEngine**
  - Replace if-elif chain with registry lookup
  - `handle_user_input` becomes ~50 lines
  - Write integration tests

### Deliverables
- All actions in separate, testable classes
- ActionRegistry for dispatch
- GameEngine `handle_user_input` under 100 lines
- 60%+ test coverage

### Files Created/Modified
```
game/
  actions/
    __init__.py      (new)
    base.py          (new)
    registry.py      (new)
    move.py          (new)
    observe.py       (new)
    inventory.py     (new)
    throw.py         (new)
    use.py           (new)
    light.py         (new)
  game_engine.py     (modified - use ActionRegistry)
tests/
  actions/
    __init__.py      (new)
    test_move.py     (new)
    test_observe.py  (new)
    test_inventory.py (new)
    test_throw.py    (new)
    test_use.py      (new)
    test_light.py    (new)
  test_action_registry.py (new)
```

---

## Phase 3: Event System & Quest Integration (Week 3-4)

**Goal:** Replace ad-hoc quest triggering with systematic event-driven approach.

### Tasks

- [ ] **3.1 Create EventBus**
  - New file: `game/events/bus.py`
  - Simple pub/sub: `emit(event_name, data)`, `subscribe(event_name, handler)`
  - Synchronous execution (no async complexity)

- [ ] **3.2 Define Event types**
  - New file: `game/events/types.py`
  - Dataclasses for each event type
  - `PlayerMovedEvent`, `ItemTakenEvent`, `PowerRestoredEvent`, etc.

- [ ] **3.3 Create QuestEventListener**
  - New file: `game/events/listeners/quest_listener.py`
  - Subscribes to relevant events
  - Calls quest_manager.check_triggers/updates/completion
  - Replaces all manual `_check_quest_*` calls

- [ ] **3.4 Create CutsceneEventListener**
  - New file: `game/events/listeners/cutscene_listener.py`
  - Subscribes to movement events
  - Triggers cutscenes on room transitions

- [ ] **3.5 Update Actions to emit events**
  - Actions return list of events in ActionResult
  - GameEngine/GameLoop emits them to EventBus
  - Remove manual quest/cutscene calls from actions

- [ ] **3.6 Write event system tests**
  - Test event emission and subscription
  - Test quest listener triggers correctly
  - Test cutscene listener triggers correctly

### Deliverables
- Decoupled event system
- Systematic quest/cutscene integration
- No manual `_check_quest_*` calls in actions
- 70%+ test coverage

### Files Created/Modified
```
game/
  events/
    __init__.py           (new)
    bus.py                (new)
    types.py              (new)
    listeners/
      __init__.py         (new)
      quest_listener.py   (new)
      cutscene_listener.py (new)
  actions/*.py            (modified - emit events)
  game_engine.py          (modified - use EventBus)
tests/
  events/
    __init__.py           (new)
    test_bus.py           (new)
    test_quest_listener.py (new)
```

---

## Phase 4: Extract Rendering & Input (Week 4-5)

**Goal:** Complete GameEngine decomposition. Add save/load.

### Tasks

- [ ] **4.1 Create RenderManager**
  - New file: `game/render/manager.py`
  - Methods: `render_room()`, `render_status()`, `render_feedback()`
  - `clear_screen()` with cross-platform support
  - Extract all rendering logic from GameEngine

- [ ] **4.2 Create TerminalAdapter**
  - New file: `game/render/terminal.py`
  - Abstract terminal operations
  - Handle raw mode, screen clearing, "press any key"
  - Graceful fallbacks for non-TTY environments

- [ ] **4.3 Create InputHandler**
  - New file: `game/input/handler.py`
  - Handle quit, quest, map shortcuts
  - Delegate to AI interpreter for complex input
  - Return Intent objects

- [ ] **4.4 Create EffectManager**
  - New file: `game/effects/manager.py`
  - Apply fear/health deltas with clamping
  - Apply inventory changes with validation
  - Currently inline in `_apply_effects()`

- [ ] **4.5 Create SaveManager**
  - New file: `game/persistence/save_manager.py`
  - `save_game(game_state, slot_name) -> Path`
  - `load_game(slot_name) -> GameState`
  - `list_saves() -> List[SaveInfo]`
  - JSON-based storage in `saves/` directory

- [ ] **4.6 Add save/load commands**
  - Add "save" and "load" to InputHandler shortcuts
  - Add to AI interpreter's allowed actions
  - Integrate with GameLoop

- [ ] **4.7 Create GameLoop (final refactor)**
  - New file: `game/game_loop.py`
  - Thin orchestrator: render → input → execute → effects → events
  - Under 100 lines
  - GameEngine becomes deprecated or alias

- [ ] **4.8 Write integration tests**
  - Test full game loop with mocked components
  - Test save/load round-trip
  - 75%+ coverage

### Deliverables
- GameEngine fully decomposed
- Clean separation of concerns
- Working save/load system
- Cross-platform terminal support
- 75%+ test coverage

### Files Created/Modified
```
game/
  render/
    __init__.py      (new)
    manager.py       (new)
    terminal.py      (new)
  input/
    __init__.py      (new)
    handler.py       (new)
  effects/
    __init__.py      (new)
    manager.py       (new)
  persistence/
    __init__.py      (new)
    save_manager.py  (new)
  game_loop.py       (new)
  game_engine.py     (deprecated - thin wrapper)
tests/
  test_render.py     (new)
  test_input.py      (new)
  test_effects.py    (new)
  test_save_load.py  (new)
  test_game_loop.py  (new)
saves/               (new directory)
```

---

## Phase 5: Parser & Polish (Week 5-6)

**Goal:** Optimize standard command handling while preserving diegetic AI for creative input.

### Design Philosophy: Diegetic Action Interpreter

**CRITICAL:** The AI is NOT a fallback — it's the core experience for creative input.

The rule-based parser should ONLY handle **trivially obvious commands**:
- "go north" / "n" / "north"
- "inventory" / "i"
- "look" / "listen"
- "take rope" / "drop stone"
- "quit" / "save" / "load"

**Everything else MUST go to the AI**, including:
- Creative actions: "breathe deeply" → AI responds in-character
- Impossible actions: "fly into the air" → AI narrates grounded failure with consequences
- Ambiguous input: "use the thing on the other thing" → AI interprets or asks diegetically
- Typos/variants: AI silently corrects and proceeds

**The AI must NEVER return:**
- "You can't do that here"
- "Invalid command"
- Any fourth-wall breaking response

**The AI must ALWAYS:**
- Respond in second-person, present tense
- Stay in-world (diegetic)
- Make failure interesting with consequences (fear, health, narrative)
- Enforce physics and lore limits through fiction, not errors

See: `docs/game_mechanics/diegetic_action_interpretor.md`  
See also: `.copilot/skills/the-cabin-diegetic.md`

### Tasks

- [ ] **5.1 Create CommandParser (narrow scope)**
  - New file: `game/input/command_parser.py`
  - ONLY handles trivially obvious commands (see list above)
  - Returns `None` for anything ambiguous → forces AI route
  - Fuzzy matching for typos on known verbs only
  - High confidence threshold (0.95+) to avoid false positives

- [ ] **5.2 Improve AI prompt for diegetic responses**
  - Update system prompt in `ai_interpreter.py`
  - Ensure impossible actions get narrated failures with consequences
  - Add examples of good/bad responses to prompt
  - Test with edge cases ("I levitate", "punch the moon", etc.)

- [ ] **5.3 Add command caching (limited scope)**
  - Cache AI responses ONLY for exact repeated commands in same context
  - Small LRU cache (50 entries max)
  - Invalidate on room change, inventory change, world state change
  - Creative commands should feel fresh, not cached

- [ ] **5.4 Improve offline fallback (graceful, not comprehensive)**
  - When API unavailable, handle only trivial commands
  - For creative commands without API: "The cold numbs your thoughts. Try something simpler."
  - Never pretend to handle creative input without AI
  - Log warning about degraded experience

- [ ] **5.5 Add type hints everywhere**
  - Run mypy in strict mode
  - Fix all type errors
  - Add to CI checks

- [ ] **5.6 Add log rotation**
  - Keep only last 10 log files
  - Clean up on startup

- [ ] **5.7 Create configuration system**
  - New file: `game/config.py`
  - Load from `config.json` or environment
  - Settings: API key, debug mode, max logs, save directory

- [ ] **5.8 Update documentation**
  - Update architecture.md to reflect new structure
  - Add developer guide for adding new actions
  - Document diegetic response requirements for AI prompt
  - Update README with new features

### Deliverables
- Fast handling of trivial commands (reduced latency/cost)
- AI remains core for creative/impossible input
- Diegetic failures for impossible actions (never "can't do that")
- Type-safe codebase
- Configuration system
- 80%+ test coverage

### Files Created/Modified
```
game/
  input/
    command_parser.py  (new)
  config.py            (new)
  logger.py            (modified - rotation)
  ai_interpreter.py    (modified - caching, error handling)
config.json            (new)
docs/
  architecture/
    architecture.md    (updated)
    developer-guide.md (new)
README.md              (updated)
```

---

## Final Directory Structure

```
the-cabin/
├── main.py                    # Entry point
├── config.json                # Configuration
├── requirements.txt           # Dependencies
├── pytest.ini                 # Test configuration
├── game/
│   ├── __init__.py
│   ├── game_loop.py           # Main game loop (orchestrator)
│   ├── game_state.py          # Unified state container
│   ├── world_state.py         # Typed world flags
│   ├── config.py              # Configuration loader
│   │
│   ├── actions/               # Action implementations
│   │   ├── __init__.py
│   │   ├── base.py            # Action ABC, ActionResult
│   │   ├── registry.py        # Action dispatch
│   │   ├── move.py
│   │   ├── observe.py         # look, listen
│   │   ├── inventory.py       # take, drop, inventory
│   │   ├── throw.py
│   │   ├── use.py
│   │   └── light.py
│   │
│   ├── events/                # Event system
│   │   ├── __init__.py
│   │   ├── bus.py             # Pub/sub event bus
│   │   ├── types.py           # Event dataclasses
│   │   └── listeners/
│   │       ├── __init__.py
│   │       ├── quest_listener.py
│   │       └── cutscene_listener.py
│   │
│   ├── input/                 # Input processing
│   │   ├── __init__.py
│   │   ├── handler.py         # Input routing
│   │   └── command_parser.py  # Rule-based parsing (trivial only)
│   │
│   ├── render/                # Display
│   │   ├── __init__.py
│   │   ├── manager.py         # Rendering logic
│   │   └── terminal.py        # Terminal abstraction
│   │
│   ├── effects/               # State changes
│   │   ├── __init__.py
│   │   └── manager.py         # Apply effects
│   │
│   ├── persistence/           # Save/load
│   │   ├── __init__.py
│   │   └── save_manager.py
│   │
│   ├── player.py              # (existing)
│   ├── map.py                 # (existing, modified)
│   ├── room.py                # (existing)
│   ├── location.py            # (existing)
│   ├── item.py                # (existing)
│   ├── wildlife.py            # (existing)
│   ├── quest.py               # (existing)
│   ├── quests.py              # (existing)
│   ├── cutscene.py            # (existing)
│   ├── requirements.py        # (existing)
│   ├── ai_interpreter.py      # (existing, modified)
│   └── logger.py              # (existing, modified)
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py            # Fixtures
│   ├── test_player.py
│   ├── test_item.py
│   ├── test_wildlife.py
│   ├── test_requirements.py
│   ├── test_world_state.py
│   ├── test_game_state.py
│   ├── test_action_registry.py
│   ├── actions/
│   │   ├── __init__.py
│   │   ├── test_move.py
│   │   ├── test_observe.py
│   │   ├── test_inventory.py
│   │   ├── test_throw.py
│   │   ├── test_use.py
│   │   └── test_light.py
│   ├── events/
│   │   ├── __init__.py
│   │   ├── test_bus.py
│   │   └── test_quest_listener.py
│   ├── test_render.py
│   ├── test_input.py
│   ├── test_command_parser.py
│   ├── test_effects.py
│   ├── test_save_load.py
│   └── test_game_loop.py
│
├── saves/                     # Save files
│   └── .gitkeep
│
├── logs/                      # (existing)
├── docs/                      # (existing, updated)
└── .copilot/
    └── skills/
        └── the-cabin-diegetic.md  # Diegetic immersion skill
```

---

## Success Criteria

| Metric | Target |
|--------|--------|
| Test coverage | ≥80% |
| GameLoop lines | <100 |
| Actions testable in isolation | ✓ |
| Trivial commands (move, inventory) work offline | ✓ |
| Creative/impossible input always gets diegetic AI response | ✓ |
| Never "you can't do that" or fourth-wall break | ✓ |
| Save/load functional | ✓ |
| Type errors (mypy strict) | 0 |
| All existing features preserved | ✓ |

---

## Risk Mitigation

1. **Regression Risk** — Mitigated by adding tests before refactoring each component
2. **Scope Creep** — Each phase has clear deliverables; resist adding features
3. **Breaking Changes** — Maintain backward compatibility during transition; deprecate don't delete
4. **Time Overrun** — Phases are independent; can pause after any phase

---

## Related Documents

- [architecture.md](./architecture.md) — Current architecture documentation
- [architectural-critique.md](./architectural-critique.md) — Analysis of current issues
- [diegetic_action_interpretor.md](../game_mechanics/diegetic_action_interpretor.md) — Core game philosophy
- [.copilot/skills/the-cabin-diegetic.md](../../.copilot/skills/the-cabin-diegetic.md) — Diegetic immersion skill
