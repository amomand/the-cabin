# The Cabin

You shouldn't have come back.  
But you did.  
It's awake.  
It always has been.


A survival horror text adventure set in the Finnish wilderness. You move through snow and timber and memory. Something old moves with you. It prefers the quiet.

---

## What is this?

**The Cabin** is a Python project experimenting with diegetic narration, light procedural generation, and a guided progression system. It stays grounded: no fourth wall, no overt systems talk — only what you feel, hear, and carry.

The game runs in the raw terminal. The screen clears as you step into each new room — as if the world is rebuilt in front of you, fresh and cold.

Core ideas:
- Room-level exploration with a clear hierarchy: Map → Locations → Rooms
- Optional exit criteria to gate progression (items, world flags, fear thresholds)
- Procedural descriptions that reflect state (power, light, weather, fear)
- The Lyer, never fully seen, always near

---

## Current status

- Raw terminal UI (no external dependencies). The terminal is cleared when you enter a new room.
- Movement parser supports basic commands like `go north`, `go south`, `go cabin`, plus `quit`.
- Room transitions happen at the room level (locations update automatically).
- World state exists (`has_power` placeholder) to support quests like the frozen fuse box.
- **Hybrid input model** — suggested actions alongside free-text parsing
- **Procedurally generated wildlife** — creatures that move through the woods, their presence felt rather than seen
- **Fear and health systems** — affecting outcomes and interactions
- **Inventory mechanics** — items that carry weight, both literal and metaphorical

Planned:
- **Expanded wilderness** — new locations, quest mechanics, and the things that hunt in the dark
- **Web interface** — a terminal-like frontend that preserves the raw, unsettling atmosphere
- **Visual mapping** — a way to see where you've been, though some places refuse to be mapped
- **Persistence** — the ability to save your progress, though the woods remember everything

---

## Project layout

```text
the-cabin/
├── main.py
├── game/
│   ├── game_engine.py      # Main loop, input handling, terminal rendering
│   ├── map.py              # Map + world_state + movement
│   ├── location.py         # Location container
│   ├── room.py             # Room model with procedural hooks
│   ├── requirements.py     # Exit criteria (items, flags, fear, custom)
│   └── player.py           # Player state (health, fear, inventory)
├── content/
│   ├── lore/               # In-universe worldbuilding (tone reference)
│   └── game_mechanics/     # Out-of-universe rules & systems
├── LICENSE
└── README.md
```

---

## Run it

Requirements: Python 3.10+

```bash
python3 main.py
```

Tips:
- If you can’t move, the game will answer in-world. Some exits require conditions to be met first.

---

## Design notes

- Diegetic principle: All feedback is in-world, second person, present tense. No system chatter.
- Hierarchy: Map manages `world_state`, holds `Location`s; each `Location` holds `Room`s. Movement is between rooms; crossing a boundary swaps locations naturally.
- Criteria: `Requirement` objects gate exits (e.g., `WorldFlagTrue("has_power")`, `HasItem("key")`, `FearBelow(60)`), returning diegetic denials if unmet.
- Procedural text: `Room.get_description(player, world_state)` layers stateful details (light, cold, memory fragments) atop static text.

For deeper tone and mechanics, see:
- `content/lore/` — names, places, weather, and the way the woods feel wrong
- `content/game_mechanics/` — parser strategy, fear/health rules, the Lyer’s constraints

---

## Contributing

Keep it quiet. Fewer exclamation marks, more winter. Match the tone in `content/lore/`. No fourth wall. Prefer small, readable edits over grand rewrites. If adding systems, thread them through the diegetic voice.

---

## License

MIT


