# Architecture Documentation

This folder contains detailed technical documentation about **The Cabin** game architecture.

## Contents

### [re-architecture-plan.md](./re-architecture-plan.md) ⭐ NEW

**Comprehensive plan to restructure the codebase (January 2026):**

- 5-phase refactoring roadmap (6-8 weeks)
- Target architecture with modular components
- GameEngine decomposition into testable units
- Event-driven quest/cutscene integration
- Save/load system
- Preserves diegetic AI as core experience

**Key Principle:** The AI is NOT a fallback — it's the core experience. Rule-based parsing only handles trivial commands. Creative input always goes to the AI for in-character responses.

### [architecture.md](./architecture.md)

**Comprehensive architecture guide covering:**

1. **Overview** - High-level introduction to the project
2. **Design Philosophy** - Core principles: diegetic immersion, atmospheric restraint, player agency
3. **High-Level Architecture** - System layers and component relationships
4. **Core Components** - Detailed breakdown of all 12 major systems:
   - GameEngine (orchestration)
   - Map (world structure)
   - Room (explorable spaces)
   - Location (area containers)
   - Player (state management)
   - Item (object system)
   - Wildlife (creature behavior)
   - AI Interpreter (natural language processing)
   - Quest System (mission structure)
   - Cutscene System (narrative moments)
   - Requirements System (gated progression)
   - Logger (debugging and tracking)
5. **Data Flow** - Four detailed flow diagrams:
   - Input processing flow
   - Movement flow
   - Quest lifecycle flow
   - Render cycle
6. **Separation of Concerns** - Five distinct layers with clear boundaries
7. **Key Design Patterns** - Nine patterns used throughout:
   - State, Strategy, Trait/Tag, Command, Observer, Template Method, Singleton, Factory, Facade
8. **Module Dependencies** - Dependency graph and principles
9. **Extension Points** - Ten detailed guides for adding:
   - New items, wildlife, rooms, locations
   - New quests, cutscenes, requirements, actions
   - Procedural descriptions and custom world state
10. **State Management** - Seven state containers explained

### [architectural-critique.md](./architectural-critique.md)

**Honest assessment of architectural strengths and weaknesses:**

1. **Major Architectural Flaws** (10 critical issues):
   - God Object Anti-Pattern (GameEngine)
   - No Test Coverage
   - Primitive State Management
   - Heavy External API Dependency
   - No Persistence System
   - Massive Input Handler Method
   - Item/Wildlife Duplication
   - Limited Quest System
   - Hardcoded Map Visualization
   - Inefficient Rendering

2. **Medium Priority Issues** (5 issues):
   - No Configuration System
   - Weak Error Handling
   - Log File Accumulation
   - Type Hints Inconsistency
   - Terminal Handling Fragility

3. **Minor Issues** - Wildlife behavior, requirements feedback, undo/history, procedural generation

4. **What's Working Well** - Trait-based systems, requirements pattern, diegetic consistency

5. **Prioritized Recommendations** - Three-tier priority system with effort estimates

6. **Refactoring Roadmap** - Four-phase plan (8-12 weeks total):
   - Phase 1: Foundation (testing, types, config)
   - Phase 2: Refactoring (break up GameEngine)
   - Phase 3: Features (save/load, expand parser)
   - Phase 4: Polish (optimization, UX)

## Quick Reference

### For Content Creators

If you want to add:
- **New items** → See "Extension Points → Adding New Items"
- **New rooms** → See "Extension Points → Adding New Rooms"
- **New quests** → See "Extension Points → Adding New Quests"
- **New cutscenes** → See "Extension Points → Adding New Cutscenes"

### For Developers

If you want to understand:
- **How input is processed** → See "Data Flow → Input Processing Flow"
- **How movement works** → See "Data Flow → Movement Flow"
- **How systems interact** → See "Separation of Concerns"
- **What patterns are used** → See "Key Design Patterns"

### For System Designers

If you want to extend:
- **New mechanics** → See "Extension Points → Adding New Actions"
- **New progression gates** → See "Extension Points → Adding New Requirements"
- **New state tracking** → See "Extension Points → Custom World State"
- **Dynamic descriptions** → See "Extension Points → Procedural Room Descriptions"

### For Refactoring/Improvement

If you want to improve the codebase:
- **What's the plan?** → See [re-architecture-plan.md](./re-architecture-plan.md) - 5-phase roadmap
- **What needs fixing?** → See [architectural-critique.md](./architectural-critique.md) - "Major Architectural Flaws"
- **Where to start?** → See "Prioritized Recommendations" (HIGH priority items)
- **Step-by-step plan?** → See "Refactoring Roadmap" (4 phases)
- **What's already good?** → See "What's Working Well" (don't break these!)
- **Core design philosophy?** → See [.copilot/skills/the-cabin-diegetic.md](../../.copilot/skills/the-cabin-diegetic.md)

## Architecture Principles

The Cabin follows these core principles:

1. **Diegetic First** - Everything stays in-world, no meta-commentary
2. **Clean Separation** - Presentation, logic, content, and services are distinct
3. **Easy Extension** - Add content without modifying core systems
4. **Minimal Coupling** - Modules interact through well-defined interfaces
5. **Atmospheric Service** - Technical design serves narrative goals

## Related Documentation

- **Game Mechanics** - `docs/game_mechanics/mechanics.md`
- **Lore & Setting** - `docs/lore/`
- **Quest Design** - `docs/game_mechanics/quests/`
- **Item Mechanics** - `docs/game_mechanics/item-mechanic.md`
- **Map Mechanics** - `docs/game_mechanics/map-mechanic.md`

## Maintenance

Update this documentation when:
- New major systems are added
- Core patterns change
- Module responsibilities shift
- New extension points are created

---

**Last Updated:** October 12, 2025  
**Document Version:** 1.0

