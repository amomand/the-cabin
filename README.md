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
pip install -r requirements.txt
cp .env.example .env   # add your OPENAI_API_KEY
python main.py
```

If the narration starts repeating itself, the game has lost its voice; the
API isn't answering. `CABIN_DEBUG=1 python main.py` will tell you why.

## Going further in

- `SETUP.md` – full setup, including the web client
- `CONTRIBUTING.md` – commands, tests, review rules. Read it before you
  change anything.
- `docs/lore/` – the plotline and what lives in it. Read `the_lyer.md` with
  the lights on.
- `docs/architecture/` – how it holds together

Keep it quiet. Fewer exclamation marks, more winter.

## License

MIT
