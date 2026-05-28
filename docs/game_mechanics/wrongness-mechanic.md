# Wrongness / Tells Mechanic

## Overview

The Wrongness system is the spine that holds Acts II–V together. As Elli moves
through the world, she observes small, specific things that are *wrong* — a
hare that doesn't breathe, frost patterned like wood grain, a smile that lands
a fraction late. Each of these is a **tell**. Tells accumulate quietly in a
**Wrongness Log**, and the count gates the story's pivot from "something is
off" to "I know what this is, and it isn't her."

Tells are observed, not chosen. Some are ambient, but the Act II forest tells
require attention: walking past the wrongness is not enough. The mechanic
exists so that the moment of recognition has weight — the player should feel
they earned it, even if they were never told they were collecting anything.

## Behaviour

- Each tell is recorded once. Re-entering the same room or repeating the same
  action does not double-count it.
- Tells are stored in insertion order and survive save/load.
- A tell can be **acknowledged** later — the data model supports this for a
  future recall or journal pass, but most beats today log it and leave it
  unacknowledged. Elli sees, then tucks it away.
- The log exposes a **threshold check** (`threshold_met(n=3)`) used by the
  Unmasking gates. Three is the current canonical value.

## Where tells live

Tells are scoped to story acts:

| Act | Anomaly | Where it fires |
|-----|---------|----------------|
| II  | `FOX_TRACKS` | `look` in the Act II cabin grounds |
| II  | `HARE` | `look` or `listen` on the Act II wood track |
| II  | `STONE_FORMATIONS` | `look` in the Act II old woods |
| III | `FROST_WOOD_GRAIN` | Wrong Cabin, once `reunion_stage == "complete"` |
| III | `KNUCKLES_BIRCH` | Wrong Cabin, once `reunion_stage == "complete"` |
| III | `DELAYED_SMILE` | Wrong Cabin, once `reunion_stage == "complete"` |
| IV  | `CORRECTION_TURN` | The definitive tell — the Wrong Outside pivot |

The Act III tells are gated behind the scripted Nika reunion: they cannot fire
until the player has progressed through `arrival → seated → complete`. This
is deliberate. The sensory wrongness only becomes *legible* once the lie is
fully inside her.

## Gates downstream

The wrongness count and presence of specific tells gate three things:

1. **The Lyer encounter** (Act II climax). In `map.py`, any attempt to leave
   `old_woods` after `first_morning` with `threshold_met(n=3)` and the player
   still in the real layer triggers the Lyer beat rather than the move.
2. **Refusal** (Act V). `refuse` requires both `recognition` set *and*
   `wrongness.threshold_met()`. Without enough tells, Elli cannot yet name
   what's wrong, so the refusal action has nothing to refuse.
3. **Acceptance** (Act V). Same gate, mirrored. The choice only opens once
   the player has seen enough.

## Authoring guidance

### Use `log_tell()`. Never raw strings.

```python
from game.story import AnomalyID, log_tell

log_tell(world_state, AnomalyID.FOX_TRACKS)
```

Do not write `world_state.wrongness.add("fox_tracks", "...")` directly in
beat code. The `log_tell()` helper looks up the canonical description from
`ANOMALY_DESCRIPTIONS` so the description string lives in exactly one place.

This is called out as a project anti-pattern in `CLAUDE.md` — "magic anomaly
strings."

### Identity, not prose

`game/story/anomalies.py` is the **identity** of every tell — the stable ID
and a short in-world description used in saved state. It is **not** where the
player-facing narration of the beat lives. The actual prose Elli reads when
she observes the anomaly belongs with the beat that fires it: a room's
`description_fn` / `wrong_description_fn`, an action in `game/actions/`, or an
observation helper in `map.py`.

This keeps the two concerns separate: the log records *that* something
wrong was seen; the room or action describes *what it felt like* to see it.

### Adding a new tell

1. Add a value to `AnomalyID` in `game/story/anomalies.py`.
2. Add a short, in-world description in `ANOMALY_DESCRIPTIONS`. Keep it under
   one line. It should read like a single observed detail, not a paragraph.
3. Call `log_tell(world_state, AnomalyID.YOUR_NEW_TELL)` at the moment of
   observation in the relevant beat. The authored prose for that moment goes
   in the beat itself, not in `anomalies.py`.
4. If the tell should gate something, check it via
   `world_state.wrongness.has(AnomalyID.YOUR_NEW_TELL.value)` or
   `threshold_met(n=N)`.
5. Add or update a dev seed in `game/devtools/seed_saves.py` so the beat is
   reachable during playtesting.

### Threshold tuning

The current canonical threshold is `3`. If you change it, change it in one
place — the call site, not the model — and update the dev seeds so the
Unmasking-adjacent seeds still cross the threshold.

## Diegetic notes

- Tells are observed silently. The player is not told they are "collecting"
  anything. There is no on-screen counter, no "1 of 3 anomalies logged"
  feedback. The mechanic must remain invisible at the surface.
- Anti-pattern: surfacing the log as a journal entry titled "Wrongness." If
  it ever becomes visible to the player, it does so as something Elli
  *remembers*, in prose, never as a list with a header.
- Tells are not "clues." Elli is not solving a mystery; she is being shown
  the truth in fragments. Authored prose around each tell should sit in
  unease, not investigation.

## Code anchors

- `game/story/anomalies.py` — `AnomalyID` enum and `ANOMALY_DESCRIPTIONS`.
- `game/story/tells.py` — `log_tell()` helper.
- `game/world_state.py` — `WrongnessEntry`, `WrongnessLog`, threshold check,
  JSON serialisation.
- `game/map.py` — Act II attention tell fires, Act IV tell fires, and the
  Lyer-encounter gate.
- `game/actions/use.py` — Act III tells (`FROST_WOOD_GRAIN`,
  `KNUCKLES_BIRCH`, `DELAYED_SMILE`) gated behind `reunion_stage == "complete"`.
- `game/actions/accept.py`, `game/actions/refuse.py` — Act V threshold +
  recognition gate.
- `game/devtools/seed_saves.py` — dev seeds that pre-populate the log.
