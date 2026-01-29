# The Cabin

You shouldn't have come back.  
It's awake.  
It always has been.

A survival horror text adventure set in the Finnish wilderness. You move through snow and timber and memory. Something old moves with you. It prefers the quiet.

---

## What is this?

**The Cabin** is a Python text adventure with AI-powered natural language input. Type anything — the game responds in-world, never breaking the fourth wall.

The game runs in the raw terminal. The screen clears as you step into each new room — as if the world is rebuilt in front of you, fresh and cold.

Core ideas:
- Free-text input interpreted by AI (gpt-5-mini)
- Diegetic responses — no "invalid command", only in-world narration
- Room-level exploration: Map → Locations → Rooms
- Fear and health mechanics that affect outcomes
- The Lyer, never fully seen, always near

---

## Quick Start

Requirements: Python 3.10+, OpenAI API key

```bash
# Install dependencies
pip install -r requirements.txt

# Set up your API key
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY

# Run
python main.py
```

---

## Features

- **Natural language input** — Type whatever you want; the AI interprets it
- **Save/load system** — `save` and `load` commands with named slots
- **231 tests** — Comprehensive test coverage
- **Modular architecture** — Actions, events, rendering all separated
- **Response caching** — Repeated commands are fast

---

## Project Layout

```
the-cabin/
├── main.py                 # Entry point
├── config.json.example     # Configuration template
├── game/
│   ├── game_engine.py      # Main orchestrator
│   ├── actions/            # 13 action classes (move, look, take, etc.)
│   ├── events/             # EventBus + listeners
│   ├── input/              # InputHandler + CommandParser
│   ├── render/             # RenderManager + TerminalAdapter
│   ├── persistence/        # SaveManager
│   ├── map.py, player.py, room.py, item.py, wildlife.py
│   └── ai_interpreter.py   # GPT integration
├── tests/                  # 231 tests
├── saves/                  # Save files
├── docs/
│   ├── architecture/       # Technical docs
│   ├── lore/               # In-universe worldbuilding
│   └── game_mechanics/     # Game rules & systems
└── README.md
```

---

## Configuration

Environment variables:
- `OPENAI_API_KEY` — Required
- `OPENAI_MODEL` — Default: gpt-5-mini
- `CABIN_DEBUG=1` — Enable debug output

Or copy `config.json.example` to `config.json`.

---

## Design Philosophy

**Diegetic immersion:** All feedback is in-world, second-person, present tense. No system chatter. The AI is the core experience — creative and impossible actions get narrated failures with consequences, never "you can't do that."

For technical details, see `docs/architecture/`.

---

## Contributing

Keep it quiet. Fewer exclamation marks, more winter. Match the tone in `docs/lore/`. No fourth wall. If adding systems, thread them through the diegetic voice.

---

## License

MIT

---

## Troubleshooting

If responses are repetitive ("You start, then think better of it..."), the API isn't working:

1. Check your `.env` has a valid `OPENAI_API_KEY`
2. Run with `CABIN_DEBUG=1 python main.py` to see API errors
3. Verify your key works: `curl https://api.openai.com/v1/models -H "Authorization: Bearer $OPENAI_API_KEY"`
