# Reunion Mechanic (Act III: the false-cabin night, arrival to bed)

## Overview

The Reunion is the Act III scripted sequence where Elli falls into the wrong
cabin and is taken care of by the thing wearing Nika. It is the warmest
sequence in the game and the most dishonest one. Mechanically, it is a state
machine over `reunion_stage` that spans the whole false-cabin night:

```
none → arrival → tended → seated → complete → consented → bedded → night → dawn
```

This doc covers the beats up to and including the bed (`arrival` through
`bedded`). The night-seam gathering and recognition are covered in
`recognition-and-refusal.md`; the dawn choice and endings live there too.

The reunion exists so the recognition that lands in Act IV is paid for. The
player has to want this Nika, has to let her clean their face and press
along their ribs, has to drink the coffee from the impossible blue mug,
before the seams can be seen for what they are. The mechanic enforces that
beat-by-beat, and every advance is a player action. The warmth is
consensual, and so is the consent beat at the door.

## Stage model

| Stage | Meaning | Advanced by |
|-------|---------|-------------|
| `none` | Not in the wrong cabin, or already out of it. Default. | — |
| `arrival` | Fallen through the door. The copy is on its feet, the green book open on the table. | `enter_wrong_layer()` (automatic) |
| `tended` | The grip, the "you called me" lie, the face cleaned, the concussion checks. | `use nika` at `arrival` |
| `seated` | The verdict ("not walking anywhere tonight"), pressed into the chair, mug in front of her. | `use nika` at `tended` |
| `complete` | First mouthful landed. Blue enamel, chip at two o'clock. The lie is inside her. Evening tells live. | `use mug` at `seated` |
| `consented` | The consent-door beat has fired: she saw the wrong outside and chose the warm room. | `move out` at `complete` (does not move her) |
| `bedded` | Mattress down, lamp off, the memory said aloud. Night seams live. | `use mattress` at `consented` |
| `night` | The knowing has finished (recognition set). | the recognition scene (see `recognition-and-refusal.md`) |
| `dawn` | The blue mug is offered. Both endings live. | `wait` at `night` |

`WorldState.reunion_complete()` is a convenience predicate for "the stage
has reached `complete`". It compares by stage order
(`reunion_stage_at_least()`), so it keeps holding through the later night
stages.

## Transitions

### `none → arrival` (automatic on layer entry)

`WorldState.enter_wrong_layer()` advances `reunion_stage` from `"none"` to
`"arrival"` as a coupled side effect. The moment Elli crashes through the
door of the wrong cabin, the copy is already on its feet.

### `arrival → tended → seated` (`use nika`, twice)

Two beats of care, both advanced by engaging with her. The arrival beat
carries the load-bearing lie: *"You called me."* Elli never called anyone;
the concussion stops her checking, and the thought sinks under the kettle.
The tended beat carries the verdict and the chair, and ends with the mug
set in front of her.

### `seated → complete` (`use mug`)

The first-mouthful beat, and the reveal that the mug is the blue mug —
whole, chip intact, hanging on a hook that was empty last night. The
narration plants that thought and files it away; it resurfaces as the
`MUG_IMPOSSIBLE` night seam. Emits `reunion_complete`.

### `complete → consented` (`move out`, once)

The consent-door beat. Elli opens the door to look for the cars and sees
the black ground, the wrong treeline, the flat starless ceiling. The copy
says the exactly right thing ("Come inside. I'm here now") and she chooses
the warm room. The move is intercepted: she does not leave the room. Sets
`consent_given = True`. Subsequent attempts to leave are held by authored
denials until the dawn choice is made.

### `consented → bedded` (`use mattress`)

The bed beat. The spare mattress, "Like when we were kids", the lamp down,
and then the copy narrates Nika's treasured memory aloud — a thing the real
Nika would die before saying. This logs `MEMORY_ALOUD` (observed, not
chosen: the first night seam arrives free). Emits `reunion_bedded`.

## Gates downstream

### The evening tells

Three tells fire only at stage `complete`, each bound to a wrong-cabin item:

| Item | Tell | Action handler |
|------|------|----------------|
| `window` | `FROST_WOOD_GRAIN` — frost patterned like wood grain | `use window` (`actions/use.py`) |
| `mug` | `KNUCKLES_BIRCH` — knuckles like knots in birch | `use mug` (`actions/use.py`) |
| `nika` | `DELAYED_SMILE` — the smile laid on a fraction late | `use nika` (`actions/use.py`) |

Before `complete`, the same `use X` actions return stage-appropriate
authored prose instead. The wrongness is not perceptible yet — that is the
point.

### The night seams

At stages `bedded`/`night`, the deliberate observations log night seams
(breathing, phone, tins, mug, boards). Those drive recognition — see
`recognition-and-refusal.md` and `wrongness-mechanic.md`.

### Room description

`_wrong_cabin_description` (`map.py`) composes the cabin's description by
stage across the whole night, surfacing logged tells and seams as callbacks,
and switching to the stopped-room description after the refusal.

### Movement guard

While the stage is short of `complete`, the movement handler blocks `out`
from `cabin_main` (she is turned back to the chair). At `complete`, the
first `out` is the consent beat. After consent, the night holds her with
authored denials. After the refusal, `out` begins the walk out — see
`world-layers-mechanic.md`.

## Authoring guidance

### The stages advance through player action, not through movement or time

Every transition is a deliberate player act: `use nika`, `use mug`,
`move out` (intercepted), `use mattress`, `wait`. Do not add an `on_enter`
or tick-based handler that advances `reunion_stage` — that's the "silent
flag flips for narrative beats" anti-pattern in `CLAUDE.md`, and worse here,
because it would let the night pass without the player choosing any of it.

### Stage-appropriate fallbacks

Every `use X` on a wrong-cabin item branches on stage even where it does
not advance. The pre-stage fallback is not a denial — it is its own
authored beat. Refer to `actions/use.py` for the canonical pattern.

### Authored prose, always

The reunion is the single most emotionally manipulative sequence in the
game. AI flavour does not write it. Per `CLAUDE.md`, AI is for intent
parsing in story-critical scenes, not for rewriting them. Never let the
model paraphrase the copy.

### The knowledge rule

The copy knows only what Nika knows, feels, or witnessed, plus anything
Elli says aloud to it. It cannot perform the estranged register. Any new
authored line for the copy must obey this — it is the escape mechanism.
The AI side is enforced too: inside the wrong layer the interpreter's
system prompt carries the same constraints (`_wrong_layer_rules()` in
`game/ai_interpreter.py`), so model flavour between the authored beats
cannot leak across the gap either.

### Resets

`exit_wrong_layer()` collapses the stage to `"none"` along with the layer
(and clears `consent_given`). Do not poke `reunion_stage` directly outside
the canonical action handlers; dev seeds in `game/devtools/seed_saves.py`
are the supported exception.

## Diegetic constraints

- The stages are invisible to the player. No progress surface, no journal.
- The pre-`complete` prose must read as the real Nika — no doorway pause,
  warmth that costs nothing. That absence of friction *is* the deception,
  and the recognition scene names it later.
- The Lyer is never named in any of this prose. The copy is "Nika" until
  the knowing finishes, then "the thing that is not Nika", and never
  anything more specific.

## Code anchors

- `game/world_state.py` — `ReunionStage` literal, `reunion_stage` field,
  `reunion_stage_at_least()`, `reunion_complete()`, `consent_given`, and
  the coupled side effects in `enter_wrong_layer()` / `exit_wrong_layer()`.
- `game/actions/use.py` — the stage handlers for `nika`, `mug`, `window`,
  `mattress`, `tins`, `phone`. Where the prose lives.
- `game/map.py` — `_wrong_cabin_description` (stage-driven room text), the
  movement guards, `_consent_door_beat`.
- `game/story/night.py` — the night-seam set and the recognition scene.
- `game/devtools/seed_saves.py` — seeds for `arrival`, `seated`,
  `consented`, `night`, `dawn`.
- Related mechanic docs: `recognition-and-refusal.md` (the knowing and the
  endings), `world-layers-mechanic.md` (layer transitions),
  `wrongness-mechanic.md` (the tell/seam log).
