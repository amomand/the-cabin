You shouldn't have come back.\
It's awake.\
It always has been.

# The Cabin

Behind you, the car ticks as it cools. The cabin stands beyond the bend, yours
on paper now. A week ago the northern camera caught three seconds of grey at
the treeline and went dark.

The Cabin is a survival horror text adventure set in northern Finland.

[Play in your browser](https://www.the-cabin.fi/game.html). No setup or API key
needed. Press a key or tap the page to begin, then type what you’d do. Try
`go north`.

## Play in a terminal

Use Python 3.10 or later. On macOS or Linux, run these from the project directory.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

Set `ANTHROPIC_API_KEY` in `.env`, then run `python main.py`.

[Configuration](docs/architecture/configuration.md) · [Contributing](CONTRIBUTING.md) · [MIT licence](LICENSE)
