# Agent Instructions

Shared guidance for coding agents and the humans reading over their shoulders.
The Cabin is a survival horror text adventure in Python 3.10+: free-text player
input, interpreted by a model, driving an authored, deterministic world.
Reference detail lives under `docs/`, story canon under `docs/lore/`. This file
is the contract; keep it lean.

Master plotline and progress notes live outside the repo, at
`~/obsidian/Fiction Writing/The Cabin/The Cabin - Plotline.md` and
`~/obsidian/Projects/the-cabin/`; read them before narrative work. Game code
is `game/`, `server/`, `tests/`, `main.py`; the iOS client is `ios/` (see
`docs/architecture/ios-client.md`); the other root files are deploy
plumbing or the static site mounted by `_mount_site()` in `server/app.py`
(prose snapshots under `stories/`, see `stories/README.md`).

## Hard rules

- All player-facing text is diegetic: second person, present tense, terse,
  bleak. Failures are narrated, with consequences. Never "invalid command",
  never "you can't do that", never system or AI talk. Fourth-wall breaks are
  bugs.
- The Lyer is implied in player-facing fiction, never explained or named
  there. In code, docs, commits, and mechanics notes, name it plainly.
- Authored story beats are canonical prose. The model parses intent; it never
  writes, rewrites, or advances story truth. Story-state transitions stay
  deterministic and narrated, never silent flag flips.
- Turn decisions live in `game/turn.py` and are shared by both surfaces.
  Never implement behaviour in only the terminal or only the web session.
- Use `AnomalyID` and `log_tell()`, never raw anomaly strings.
- Entry points own `.env` loading. Tests, seeds, and offline playtests must
  never make live model calls.
- Commits do one thing. Don't bundle unrelated changes.

## Commands

```bash
pip install -r requirements-dev.txt    # full dev set; needed before pytest
python main.py                         # run the game (needs OPENAI_API_KEY)
python -m pytest                       # tests (no API key needed)
python -m tools.playtest_runner        # offline playtest scenarios
python -m game.devtools.seed_saves list  # dev seeds for story beats
```

## Pull requests

- Work in draft. Run the applicable local skills in `.agents/skills/` against
  the final diff (diegesis review for player-facing prose or response
  behaviour, continuity review for docs, mechanics, and contracts) and record
  the verdicts in the PR.
- Routine work (documentation, tests, or mechanical changes that alter no
  behaviour or contract) carries the write-controlled `review:routine` label.
  Hosted review is advisory there; don't wait for it.
- Everything else is Reviewed work: it gets one completed review of the exact
  current head by a hosted reviewer outside every authoring family; use the
  `copilot-pr-review-loop` skill. Give every finding a visible reply: fixed,
  already covered, outdated, or overridden with the reason.
- Changes touching story truth, turn or state parity across surfaces, offline
  isolation, or validation and publication meaning also get the
  `adversarial-review` skill against the committed head.
- Record authoring families and review depth under `Review provenance` in the
  PR body; the gate parses the `Authoring agent(s):` line and the label. Mark
  the PR ready once review work and CI are green. Never merge; the maintainer
  merges.
- Stacked PRs: read `docs/architecture/stacked-prs.md` before merging any
  child.

The weekly scheduled playtest review is a separate system and never a PR gate;
see `docs/architecture/agentic-playtest-review.md`.
