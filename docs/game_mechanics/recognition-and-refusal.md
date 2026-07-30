# Recognition & Refusal (Acts IV–V Mechanic)

## Overview

This is the endgame arc of the rewritten canon (issue #141). After the
consent beat and the bed beat (see `reunion-mechanic.md`), the night turns
the player's deliberate observations into the knowing, and the knowing into
the dawn choice:

1. **The night seams** — the **Act IV gathering**. Lying in the dark beside
   the copy, the player observes: the breathing that never varies, the
   phone that will not wake, the tins, the impossible mug, the boards going
   black. Each logs a seam in the wrongness log.
2. **The knowing (recognition)** — at the seam threshold, the authored
   recognition scene fires on the observation that crossed it. The flaw
   under everything: *it didn't hurt*. Sets `recognition`.
3. **The dawn choice** — `wait` brings the wrong grey morning and the
   offered blue mug. Declining it is the refusal (the escape). Drinking it
   is the stayed ending.

Then the walk out (playable, three moves south through indifferent woods)
and the coda (the phone call, the scraping, the final `wait`).

The mechanic exists so the recognition feels earned by attention rather
than delivered by a cutscene, and so the choice is bounded: Elli cannot
refuse what she has not recognised.

## State model

| Field | Type | Meaning |
|-------|------|---------|
| `recognition` | `bool` | The knowing has finished. Set only inside the recognition scene. **Not** reset by `exit_wrong_layer()`. |
| `consent_given` | `bool` | The consent-door beat fired and she chose the warm room. Reset by `exit_wrong_layer()`. |
| `ending` | `"none" \| "escaped" \| "stayed"` (legacy `accepted`/`refused` still parse for old saves) | Which dawn choice landed. Persisted. |
| `coda_stage` | `"none" \| "home" \| "called" \| "scraping" \| "end"` | Coda progression after the escape. Persisted. |

The threshold dependency is the **night-seam count**:
`night_threshold_met()` in `game/story/night.py` — currently 4 of the
night-seam set (`memory_aloud`, `breathing_tide`, `phone_dark`,
`wrong_tins`, `black_boards`, `mug_impossible`). `MEMORY_ALOUD` arrives
free with the bed beat; the player gathers at least three more.

## The beats

### 1. Night seams (stage `bedded`/`night`, wrong cabin)

| Observation | Seam | Where it fires |
|-------------|------|----------------|
| `listen` | `BREATHING_TIDE` | `map.observe_current_room` |
| `look` | `BLACK_BOARDS` | `map.observe_current_room` |
| `use phone` | `PHONE_DARK` | `actions/use.py` |
| `use tins` | `WRONG_TINS` | `actions/use.py` |
| `use mug` | `MUG_IMPOSSIBLE` | `actions/use.py` |
| (bed beat) | `MEMORY_ALOUD` | `use mattress`, automatic |

Each observation is authored prose; each logs once and re-narrates without
double-counting.

### 2. The knowing (`game/story/night.py:maybe_finish_the_knowing`)

Called by every beat that logs a night seam. When the threshold is crossed
(and stage is `bedded`/`night`, and recognition hasn't fired), it:

- logs `NO_CALL` (the "you called me" lie joins the log as part of the
  knowing),
- sets `recognition = True` and `reunion_stage = "night"`,
- returns the authored recognition scene, which the calling beat appends
  to its own feedback.

This is the only place `recognition` is set in production code (dev seeds
excepted). Recognition is a scene, not a flag flip: the scene rides on the
observation that earned it.

### 3. Dawn (`actions/wait.py`)

`wait` at stage `night` with recognition brings the dawn beat: the copy
rises without waking, pours coffee into the blue mug, holds it out.
*"Drink up. We'll want the light."* Sets `reunion_stage = "dawn"`. The
offer is now live, and movement out of the room is held by the offer
itself.

### 4. The two endings (`actions/refuse.py`, `actions/accept.py`)

Both gate on `recognition AND night_threshold_met()`, then on being at the
dawn offer (`cabin_main`, stage `dawn`). Every guard returns
stage-appropriate authored prose, never a denial.

- **Refuse** (the canon ending, The Escape): the register change, the
  estrangement spoken, the grief spent back, the voicemail completed
  ("it's lying out there"), the pretence stopping, the attention
  withdrawing like a book being closed. Sets `ending = "escaped"`. She
  stays in the wrong layer: the walk out happens on foot. Declining the
  offered mug in words ("no thank you") routes here via the interpreter.
- **Accept** (deliberately off-canon): drinking the coffee. `use mug` at
  dawn routes through `AcceptAction` so the prose has one home. Sets
  `ending = "stayed"` and closes the run (`game/ending.py`,
  `END_LINE_STAYED`). The horror is consent, not damnation — the room is
  warm, the smile arrives on time now, first light never comes.

### 5. The walk out (`map.py`)

After the refusal, `out` then `south` then `south`: the threshold beat,
the indifferent-woods beat (mattering to nothing, the two falls), and the
arrival home (`_arrive_home`: exits the layer, lands at the real wood
store, sets `coda_stage = "home"`). No pursuit. Nothing arranges itself.

### 6. The coda (`actions/use.py` phone, `actions/wait.py`)

In the real cabin: `use phone` makes the call (the pause with twenty years
in it, "Drive slow"; `coda_stage = "called"`). `wait` starts the scraping
(`"scraping"`), and a final `wait` sits her in her grandmother's chair,
facing the empty hook, listening (`"end"`). The run closes with
`END_LINE_ESCAPED` ("You wait.").

## Why the dual gate

Refuse and Accept gate on `recognition AND night_threshold_met()`. Either
alone is insufficient: seams without recognition are just unease, and
recognition without seams should not be reachable by normal play (the
scene only fires at the threshold). The dual gate is a safety so a dev
seed or malformed save cannot open the choice with no earned weight.

Enforced in three places that must stay in sync:

- The action handlers (`refuse.py`, `accept.py`).
- The AI's `_act_v_offer_active()` predicate (`ai_interpreter.py`): live
  only when `recognition AND world_layer == "wrong" AND ending == "none"
  AND reunion_stage == "dawn" AND room_id == "cabin_main" AND night seams
  >= threshold`.
- The interpreter's rule-based dawn synonyms ("no thank you" → refuse,
  "drink up" → accept), gated on the same predicate.

## Authoring guidance

- **Recognition is a scene, not a flag flip.** `recognition` is set inside
  `maybe_finish_the_knowing()` alongside the prose that earns it. Do not
  flip it from an `on_enter` callback or ambient handler. Same for
  `ending` and `coda_stage`: they change only inside the authored beats.
- **Pre-recognition denials are their own beats.** Every guard returns
  authored prose about Elli's incomplete understanding, not a rejection of
  input.
- **Endings live in the action handlers**, inline and authored. Never let
  the model paraphrase them.
- **The choice is located.** The offer is the mug at dawn in the false
  cabin. Do not extend the gate to other rooms or stages casually.
- **Reset semantics.** `exit_wrong_layer()` (called by `_arrive_home`)
  clears `reunion_stage`, `wrong_outside_seen`, and `consent_given`. It
  does **not** clear `recognition`, `ending`, or `coda_stage`. Returning to
  the real world is not amnesia.

## Diegetic constraints

- The flags are invisible. The arc is felt, not displayed.
- Neither ending names what was offered. The Lyer is never named in
  player-facing prose; the naming is carried by the voicemail line.
- The stayed ending is not punitive. The room is warm and stays warm.
  New authored content must hold that line.

## Code anchors

- `game/story/night.py` — the seam set, threshold, recognition scene,
  `maybe_finish_the_knowing()`.
- `game/world_state.py` — `recognition`, `consent_given`, `ending`,
  `coda_stage`, reset semantics.
- `game/actions/wait.py` — dawn turn, scraping, the final wait.
- `game/actions/refuse.py` / `accept.py` — the endings.
- `game/actions/use.py` — night seams on phone/tins/mug; the coda call.
- `game/map.py` — night look/listen seams, the walk-out beats,
  `_arrive_home`, the coda cabin description.
- `game/ending.py` — closing lines shared by terminal and web.
- `game/ai_interpreter.py` — `_act_v_offer_active()` and the dawn synonym
  sets.
- `game/devtools/seed_saves.py` — `act4_night`, `act4_recognition`,
  `act5_dawn`, `coda_home`.
