# Wrongness / Tells Mechanic

## Overview

The Wrongness system is the spine that holds Acts II–V together. As Elli moves
through the world, she observes small, specific things that are *wrong* — a
hare that doesn't breathe, frost patterned like wood grain, a smile that lands
a fraction late. Each of these is a **tell**. Tells accumulate quietly in a
**Wrongness Log**, and the count gates the story's pivot from "something is
off" to "I know what this is, and it isn't her."

The Act II forest tells land on arrival along the authored walk. Attention also
supports loaded positions, using the same one-shot helper in `game/story/morning.py`.
Room rendering never logs a tell. Later looks recall the fox or hare without
re-encountering either; repeat entry does not replay the discovery. The camera
errand has its own state and cannot be completed by looking at the fox tracks.

## Behaviour

- Each tell is recorded once. Re-entering the same room or repeating the same
  action does not double-count it.
- Tells are stored in insertion order and survive save/load.
- A tell can be **acknowledged** later — the data model supports this for a
  future recall or journal pass, but most beats today log it and leave it
  unacknowledged. Elli sees, then tucks it away.
- The log exposes a general `threshold_met(n=3)` query. Story gates use the
  relevant subset: the three specific forest tells for the encounter, and the
  night-seam count for recognition.

## Where tells live

Tells are scoped to story acts:

| Act | Anomaly | Where it fires |
|-----|---------|----------------|
| II  | `FOX_TRACKS` | Morning arrival at the cabin grounds; `look` supports a loaded position |
| II  | `HARE` | Arrival at Dead Pines (`deer_path`); `look`/`listen` support a loaded position |
| II  | `STONE_FORMATIONS` (legacy save ID) | Arrival in Old Woods; `look` supports a loaded position |
| III | `FROST_WOOD_GRAIN` | `use window` at `complete`, or automatically before consent |
| III | `KNUCKLES_BIRCH` | `use mug` at `complete`, or automatically before consent |
| III | `DELAYED_SMILE` | `use nika` at `complete`, or automatically before consent |
| IV  | `MEMORY_ALOUD` | The bed beat (`use mattress`), automatic |
| IV  | `BREATHING_TIDE` | `listen` at stage `bedded`/`night` |
| IV  | `BLACK_BOARDS` | `look` at stage `bedded`/`night` |
| IV  | `PHONE_DARK` | `use phone` at stage `bedded`/`night` |
| IV  | `WRONG_TINS` | `use tins` at stage `bedded`/`night` |
| IV  | `MUG_IMPOSSIBLE` | `use mug` at stage `bedded`/`night` |
| IV  | `NO_CALL` | Logged inside the recognition scene |

(`CORRECTION_TURN` is a legacy v1 anomaly, kept only so old saves load.)

The Act III tells are gated behind the scripted reunion: they cannot fire until
the player has progressed through `arrival → tended → seated → complete`.
Close looks can gather them at `complete`; the consent-door beat narrates and
logs any still missing before advancing to `consented`. The scene order stays
fixed even if the player examines its fixtures out of order, and repeat looks
use callbacks instead of replaying a tell. The Act IV night seams are gated
behind the bed beat. This is deliberate. The sensory wrongness only
becomes *legible* once the lie is fully inside her, and none of it can be
skipped by walking straight to the door.

## Gates downstream

The wrongness count and presence of specific tells gate three things:

1. **The Lyer encounter** (Act II climax). In `map.py`, any attempt to leave
   `old_woods` after `first_morning`, with `camera_errand_done` and each of
   `FOX_TRACKS`, `HARE` and `STONE_FORMATIONS`, triggers the Lyer beat rather
   than the move. The player must still be in the real layer, with no ending
   and no previous encounter. Unrelated tells cannot substitute.
2. **Recognition** (Act IV). The knowing finishes when the night-seam count
   reaches `NIGHT_SEAM_THRESHOLD` (currently 4 of the night-seam set), with
   the unvarying breath among them. Any canonical seams still unseen then
   land before the recognition scene. See `game/story/night.py` and
   `recognition-and-refusal.md`.
3. **The dawn endings** (Act V). `is_dawn_offer_active()` requires
   `recognition` *and* `night_threshold_met()`, along with the live false-cabin
   offer. Without the gathered seams, Elli cannot yet name what there is to
   say no to.

## Authoring guidance

### Use `log_tell()`. Never raw strings.

```python
from game.story import AnomalyID, log_tell

log_tell(world_state, AnomalyID.FOX_TRACKS, player)
```

Do not write `world_state.wrongness.add("fox_tracks", "...")` directly in
beat code. The `log_tell()` helper looks up the canonical description from
`ANOMALY_DESCRIPTIONS` so the description string lives in exactly one place.

This is called out as a project anti-pattern in `AGENTS.md` — "magic anomaly
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

The third Act II tell keeps the serialized value `stone_formations` for old-save
compatibility. It no longer puts formations or engravings into the fiction.
Current prose records the vanished deer path and the forest emptied of animal
life, in keeping with the published story.

### Adding a new tell

1. Add a value to `AnomalyID` in `game/story/anomalies.py`.
2. Add a short, in-world description in `ANOMALY_DESCRIPTIONS`. Keep it under
   one line. It should read like a single observed detail, not a paragraph.
3. Call `log_tell(world_state, AnomalyID.YOUR_NEW_TELL, player)` at the moment
   of observation in the relevant beat. The authored prose for that moment goes
   in the beat itself, not in `anomalies.py`.

   **Pass the player.** The argument is optional so dev seeds and tests can
   build wrongness state without one, which means a tell that omits it still
   logs, still gates, and silently costs nothing - nothing fails to catch it.
   A newly logged tell is worth `fear.TELL_OBSERVED`; see
   `docs/game_mechanics/fear-curve.md`.
4. If the tell should gate something, check it via
   `world_state.wrongness.has(AnomalyID.YOUR_NEW_TELL.value)` or
   `threshold_met(n=N)`.
5. Add or update a dev seed in `game/devtools/seed_saves.py` so the beat is
   reachable during playtesting.

### Threshold tuning

The Act II encounter requires all three specific forest tells plus the camera
comparison. The Act IV recognition gate is `NIGHT_SEAM_THRESHOLD`
(currently 4) over the night-seam subset in `game/story/night.py`, with
`BREATHING_TIDE` required before recognition. If you change a gate, change it
at its single definition site and update the dev seeds so the adjacent seeds
still cross it.

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
- `game/story/evening.py` — Act III evening-tell order and shared narration.
- `game/story/night.py` — the night-seam set, `NIGHT_SEAM_THRESHOLD`, and
  `maybe_finish_the_knowing()`.
- `game/story/dawn.py` — shared truth for advancing to dawn and answering the
  active offer.
- `game/world_state.py` — `WrongnessEntry`, `WrongnessLog`, threshold check,
  JSON serialisation.
- `game/story/morning.py` — camera stages, forest discoveries and callbacks.
- `game/map.py` — movement and attention delivery, the night look/listen seams,
  and the Lyer-encounter gate.
- `game/actions/use_handlers/false_cabin.py` — optional Act III close looks
  at `complete`; night seams on tins/mug.
- `game/actions/use_handlers/phone.py` — the phone night seam.
- `game/actions/accept.py`, `game/actions/refuse.py` — consume the active-offer
  predicate before landing an ending.
- `game/devtools/seed_saves.py` — dev seeds that pre-populate the log.
