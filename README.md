# The Cabin

You shouldn't have come back.  
It's awake.  
It always has been.

A survival horror text adventure set in the Finnish wilderness. You move through snow and timber and memory. Something old moves with you. It prefers the quiet.

---

## What is this?

**The Cabin** is a Python text adventure with AI-powered natural language input. Type anything; the game responds in-world, never breaking the fourth wall.

The game can run in the raw terminal or through the lightweight browser client. The screen clears as you step into each new room, as if the world is rebuilt in front of you, fresh and cold.

Core ideas:
- Free-text input interpreted by AI (`gpt-5.4-mini` by default)
- Diegetic responses: no "invalid command", only in-world narration
- Room-level exploration: Map -> Locations -> Rooms
- Fear, health, save/load, quest, event, and cutscene systems
- Act I-V plotline with wrong-layer cabin states and physical ending choices
- The Lyer, never fully seen, always near

---

## Quick Start

Requirements: Python 3.10+, OpenAI API key

Command examples use `python`. On systems where only `python3` is available,
use `python3` instead, or use the interpreter from an activated virtual
environment.

```bash
# Install base Python dependencies
pip install -r requirements.txt

# Set up your API key
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY

# Run in the terminal
python main.py
```

To run the web client locally:

```bash
pip install -r requirements-server.txt
python -m uvicorn server.app:app --reload --port 8080
```

In another terminal, serve the browser client from the repo root:

```bash
python -m http.server 8000
```

Then open `http://localhost:8000/play.html` in a browser.

---

## Development Checks

Install the full development/test environment before running the complete
suite. This includes the terminal game, web server, pytest, and playtest runner
dependencies used by CI.

```bash
pip install -r requirements-dev.txt
python -m pytest
python -m tools.playtest_runner
python -m pytest --cov=game --cov=server --cov-report=term-missing
```

---

## Features

- **Natural language input** - Type whatever you want; the AI interprets it
- **Diegetic command handling** - Creative, impossible, save/load, and help paths stay in-world
- **Save/load system** - `save` and `load` commands with named slots
- **Dev seed saves** - Jump to known story beats for playtesting
- **Local playtest scenarios** - Drive terminal/web sessions and capture transcripts
- **Python test suite** - Coverage across actions, story beats, web session flow, persistence, and AI hardening
- **Modular architecture** - Actions, events, rendering, input, persistence, and web sessions are separated
- **Response caching** - Repeated commands are fast
- **Local PR review skills** - Diegesis and continuity reviews catch immersion and story-consistency drift before PRs

---

## Story And Lore

The story canon is documented in `docs/lore/plotline.md`, a dated snapshot of the maintainer's living plotline. The playable story extends through Acts I-V, including the wrong cabin, recognition, and accept/refuse endings; from Act III onwards it realises an earlier iteration of that canon (see the status note at the top of `plotline.md`).

Supporting lore files live in `docs/lore/`:
- `characters.md`
- `environment-setting.md`
- `the_lyer.md`

Those files provide worldbuilding context, while `plotline.md` carries the current story canon for the Act I-V arc.

---

## Dev Seed Saves

Named seed saves make playtesting later acts easier:

```bash
python -m game.devtools.seed_saves list
python -m game.devtools.seed_saves generate
python -m game.devtools.seed_saves use act3_arrival
```

After `use`, start the game and load the seed by name, for example `load act3_arrival`.

Available seeds currently include:
- `act1_end`
- `act2_mid`
- `act3_arrival`
- `act3_seated`
- `act4_recognition`

## Local Playtest Runner

The local playtest runner drives real terminal or web-session game objects,
checks their visible output, and writes transcripts under `reports/playtests/`
(ignored by git).

```bash
python -m tools.playtest_runner
python -m tools.playtest_runner playtests/scenarios/act1_smoke.yaml
```

Scenarios live in `playtests/scenarios/`. They run offline by default so
deterministic smoke paths do not call the OpenAI API. Use the reports as PR
evidence alongside the local diegesis and continuity review skills.

---

## Project Layout

```text
the-cabin/
├── main.py                 # Terminal entry point
├── play.html               # Browser client
├── server/                 # FastAPI WebSocket session server
├── config.json.example     # Configuration template
├── requirements-dev.txt    # Development/test dependency set
├── game/
│   ├── game_engine.py      # Main orchestrator
│   ├── actions/            # 15 action classes, including Act V accept/refuse
│   ├── events/             # EventBus + listeners
│   ├── input/              # InputHandler + legacy parser helpers
│   ├── persistence/        # SaveManager
│   ├── devtools/           # Playtest seed-save tools
│   ├── map.py, player.py, room.py, item.py, wildlife.py
│   └── ai_interpreter.py   # GPT integration + rule-based command handling
├── tests/                  # Python test suite
├── playtests/scenarios/    # Local playtest scenario briefs
├── tools/playtest_runner.py # Local transcript-producing playtest runner
├── saves/                  # Save files
├── docs/
│   ├── architecture/       # Technical docs
│   ├── lore/               # Plotline and worldbuilding
│   └── game_mechanics/     # Game rules and systems
├── .codex/skills/          # Local pre-PR review skills
└── .github/workflows/      # Deploy workflow
```

---

## Configuration

Environment variables:
- `OPENAI_API_KEY` - Required
- `OPENAI_MODEL` - Default: `gpt-5.4-mini`
- `OPENAI_REASONING_EFFORT` - Default: `none`
- `CABIN_DEBUG=1` - Enable debug output

Or copy `config.json.example` to `config.json`.

---

## Design Philosophy

**Diegetic immersion:** all feedback is in-world, second-person, present tense. No system chatter. The AI is the core experience: creative and impossible actions get narrated failures with consequences, never "you can't do that."

**Continuity matters:** the story contract is protected by tests and local pre-PR review skills. Diegesis review watches for fourth-wall leaks and tone breaks; continuity review watches for contradictions between implementation, docs, and the current plotline.

For technical details, see `docs/architecture/`.

---

## Contributing

Keep it quiet. Fewer exclamation marks, more winter. Match the tone in `docs/lore/`. No fourth wall. If adding systems, thread them through the diegetic voice and update the architecture, plotline, and README when behavior or canon changes.

---

## License

MIT

---

## Troubleshooting

If responses are repetitive ("You start, then think better of it..."), the API isn't working:

1. Check your `.env` has a valid `OPENAI_API_KEY`
2. Run with `CABIN_DEBUG=1 python main.py` to see API errors
3. Verify your key works: `curl https://api.openai.com/v1/models -H "Authorization: Bearer $OPENAI_API_KEY"`
