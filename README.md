# The Cabin

You shouldn't have come back.\
It's awake.\
It always has been.

A survival horror text adventure set in the Finnish wilderness. You type what
you would try; an AI reads it and answers inside an authored, deterministic
world. No system chatter, no "invalid command". Only what happens next.

**[Play online](https://the-cabin-api.fly.dev/game.html)** – no setup, no API
key. The door is already open.

## Run it yourself

Your own copy needs a voice: Python 3.10+ and an OpenAI API key.

```bash
# Keep the cold contained
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

pip install -r requirements.txt
cp .env.example .env        # add your OPENAI_API_KEY
python main.py
```

For the browser client, add the server set and run both halves:

```bash
pip install -r requirements-server.txt
python -m uvicorn server.app:app --reload --port 8080
python -m http.server 8000   # second terminal, repo root
```

Then open `http://localhost:8000/play.html`.

If free-form actions keep drawing the same short replies while plain commands
still work, the game has lost its voice; the interpreter has fallen back
offline. `CABIN_DEBUG=1 python main.py` will tell you why.

## Going further in

- `AGENTS.md` – commands, tests, review rules. Read it before you change
  anything.
- `docs/architecture/` – configuration, playtesting, and how it holds together
- `docs/lore/` – the plotline and what lives in it. Read `the_lyer.md` with
  the lights on.

Keep it quiet. Fewer exclamation marks, more winter.

## License

MIT
