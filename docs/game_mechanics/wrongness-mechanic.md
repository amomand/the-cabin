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
| IV  | `MEMORY_ALOUD` | The bed beat (`use mattress`), automatic |
| IV  | `BREATHING_TIDE` | `listen` at stage `bedded`/`night` |
| IV  | `BLACK_BOARDS` | `look` at stage `bedded`/`night` |
| IV  | `PHONE_DARK` | `use phone` at stage `bedded`/`night` |
| IV  | `WRONG_TINS` | `use tins` at stage `bedded`/`night` |
| IV  | `MUG_IMPOSSIBLE` | `use mug` at stage `bedded`/`night` |
| IV  | `NO_CALL` | Logged inside the recognition scene |

(`CORRECTION_TURN` is a legacy v1 anomaly, kept only so old saves load.)

The Act III tells are gated behind the scripted reunion: they cannot fire
until the player has progressed through `arrival → tended → seated →
complete`. The Act IV night seams are gated behind the bed beat. This is
deliberate. The sensory wrongness only becomes *legible* once the lie is
fully inside her, and the seams only become gatherable once she is lying
in the dark beside it.

## Gates downstream

The wrongness count and presence of specific tells gate three things:

1. **The Lyer encounter** (Act II climax). In `map.py`, any attempt to leave
   `old_woods` after `first_morning` with `threshold_met(n=3)` and the player
   still in the real layer triggers the Lyer beat rather than the move.
2. **Recognition** (Act IV). The knowing finishes when the night-seam count
   reaches `NIGHT_SEAM_THRESHOLD` (currently 4 of the night-seam set) —
   see `game/story/night.py` and `recognition-and-refusal.md`.
3. **The dawn endings** (Act V). Both `refuse` and `accept` require
   `recognition` *and* `night_threshold_met()`. Without the gathered
   seams, Elli cannot yet name what there is to say no to.

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

There are two thresholds. The Act II encounter gate is `threshold_met(n=3)`
over the whole log. The Act IV recognition gate is `NIGHT_SEAM_THRESHOLD`
(currently 4) over the night-seam subset in `game/story/night.py`. If you
change either, change it at its single definition site and update the dev
seeds so the adjacent seeds still cross it.

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
- `game/story/night.py` — the night-seam set, `NIGHT_SEAM_THRESHOLD`, and
  `maybe_finish_the_knowing()`.
- `game/world_state.py` — `WrongnessEntry`, `WrongnessLog`, threshold check,
  JSON serialisation.
- `game/map.py` — Act II attention tells, the night look/listen seams, and
  the Lyer-encounter gate.
- `game/actions/use.py` — Act III tells gated behind
  `reunion_stage == "complete"`; night seams on phone/tins/mug.
- `game/actions/accept.py`, `game/actions/refuse.py` — the dawn gate
  (recognition + night threshold).
- `game/devtools/seed_saves.py` — dev seeds that pre-populate the log.
