# Reunion Mechanic (Act III)

## Overview

The Reunion is the Act III scripted beat where Elli sits across the table
from Nika in the wrong cabin. It is the warmest scene in the game and the
most dishonest one. Mechanically, it is a small state machine over
`reunion_stage` — the v1 beats use `"none" | "arrival" | "seated" |
"complete"` — that gates the emotional weight of the lie and the sensory
wrongness that follows it. (The literal also carries later night stages,
`tended/consented/bedded/night/dawn`, as foundations for the rewritten-canon
arc; no v1 beat sets them yet. See issue #141.)

The reunion exists so the recognition that lands in Act IV is paid for. The
player has to want this Nika, has to sit with her, has to drink the coffee
exactly the way she takes it, before the tells can fire. The mechanic
enforces that beat-by-beat.

## Stage model

```
none ──(enter_wrong_layer)──▶ arrival ──(use nika)──▶ seated ──(use mug)──▶ complete
  ▲                                                                            │
  └────────────────────── (exit_wrong_layer / refuse / accept) ────────────────┘
```

| Stage | Meaning | Authored prose lives in |
|-------|---------|-------------------------|
| `none` | Not in the wrong cabin yet, or already refused/accepted out of it. Default. | — |
| `arrival` | Elli has fallen through the door. Nika is on her feet, assessing. No-one is seated yet. | `_wrong_cabin_description` (`map.py`) + `use nika` arrival branch (`actions/use.py`) |
| `seated` | Nika has pressed Elli into a chair. Coffee is in front of her, not yet tasted. | `_wrong_cabin_description` seated branch + `use mug` seated branch |
| `complete` | First mouthful has landed. The reunion lie is inside her. Sensory tells can now surface. | `_wrong_cabin_description` complete branch + tell narrations on `window` / `mug` / `nika` |

`WorldState.reunion_complete()` is a convenience predicate for the common
`stage == "complete"` check.

## Transitions

### `none → arrival` (automatic on layer entry)

`WorldState.enter_wrong_layer()` advances `reunion_stage` from `"none"` to
`"arrival"` as a coupled side effect. This is deliberate: the moment Elli
crashes through the door of the wrong cabin, Nika is already on her feet.
There is no separate "start the reunion" call site.

### `arrival → seated` (`use nika`)

Triggered by the player using/addressing Nika while `stage == "arrival"`.
The authored prose covers her grip, the questions ("Where have you been?",
"Running from what?"), and her pressing Elli into the chair. The mug
appears on the table at the end of the beat. The handler sets
`reunion_stage = "seated"` and emits the `reunion_seated` event.

### `seated → complete` (`use mug`)

The first-mouthful beat. Triggered by the player using the mug while
`stage == "seated"`. This is the emotional pivot — coffee made exactly
how Elli takes it, the old closeness suddenly present in the room as
though no time has passed. The handler sets `reunion_stage = "complete"`
and emits both `use_mug` and `reunion_complete` events.

### `complete → none` (exit endings)

`WorldState.exit_wrong_layer()` resets `reunion_stage` to `"none"`. Both
endings — `actions/refuse.py` and `actions/accept.py` — call this. The
refusal dissolves the reunion along with the wrong cabin; the acceptance
collapses it for a different reason. Either way, the reunion is not a
place Elli remains in.

## Gates downstream

### The Act III sensory tells

The three Act III tells fire only after `stage == "complete"`. Each is
bound to one of the wrong-cabin items:

| Item | Tell | Action handler |
|------|------|----------------|
| `window` | `FROST_WOOD_GRAIN` — frost patterned like wood grain | `use window` (`actions/use.py`) |
| `mug` | `KNUCKLES_BIRCH` — Nika's knuckles like knots in birch wood | `use mug` (`actions/use.py`) |
| `nika` | `DELAYED_SMILE` — the smile laid across the face a fraction late | `use nika` (`actions/use.py`) |

Before `complete`, the same `use X` actions return stage-appropriate
authored prose instead (the window with no sun in it, the untouched mug,
Nika watching you wait). The wrongness is not perceptible yet — that is
the point.

### Room description

`_wrong_cabin_description` composes the cabin's description by
`reunion_stage`. At `arrival` and `seated` it returns fixed authored prose.
At `complete`, it surfaces whichever tells have been logged as callbacks
inside the room description, so re-entering or re-looking around the room
echoes what Elli has seen.

### Movement guard

While `stage` is not `complete` and the layer is wrong, the movement
handler in `map.py` blocks `direction == "out"` from `cabin_main`. Nika
catches Elli's arm and turns her back to the chair. The lie works
precisely by keeping her inside it. Once `reunion_complete()` is true the
guard releases and the Wrong Outside pivot becomes reachable.

### Wrong Outside pivot

The `wrong_outside_seen` one-shot fires when Elli first steps from
`cabin_main` to `cabin_clearing` in the wrong layer **after** the reunion
completes. The reunion is therefore a hard prerequisite for the Act IV
opening.

## Authoring guidance

### The stages advance through `use`, not through movement

The arrival → seated and seated → complete transitions are both player
actions on items inside the wrong cabin (`use nika`, `use mug`). They are
not advanced by entering a room, by time passing, or by any ambient
handler. This is intentional: the player has to choose to engage with the
lie at each step. The mechanic enforces that the warmth is consensual.

Do not add an `on_enter` or tick-based handler that advances
`reunion_stage`. That's the "silent flag flips for narrative beats"
anti-pattern in `CLAUDE.md` — and worse here, because it would let the
reunion complete without the player ever sitting at the table.

### Stage-appropriate fallbacks

Every `use X` on a wrong-cabin item should branch on `stage` even at
stages where it does not advance. Look at the `window` handler: before
`complete`, it returns "the light outside is flat and white, with no sun
in it. You don't look for long. Not yet." After `complete`, it fires the
frost tell. The pre-stage fallback is not a denial — it is its own
authored beat. Refer to `actions/use.py` for the canonical pattern.

### Authored prose, always

The reunion is the single most emotionally manipulative scene in the
game. AI flavour does not write it. Per `CLAUDE.md`, AI is for intent
parsing in story-critical scenes, not for rewriting them. If a player
types something the reunion handlers don't recognise, route through the
generic fallback — never let the model paraphrase Nika.

### Resets

If you need to test or replay the reunion, `exit_wrong_layer()` is the
correct reset path — it collapses the stage to `"none"` along with the
layer. Do not write code that pokes `reunion_stage` directly to advance
or rewind it outside of the canonical action handlers; dev seeds in
`game/devtools/seed_saves.py` are the supported exception and exist
precisely so playtesting can jump to a known stage.

## Diegetic constraints

- The stages are invisible to the player. No "Reunion: 2 of 3" surface,
  no log, no journal entry. The mechanic must remain entirely beneath the
  fiction.
- The reunion is not framed as a puzzle or a sequence to be completed.
  Authored prose around each beat sits in warmth and grief, not progress.
- The wrong cabin is the same cabin until the tells start. The pre-`complete`
  prose must never tip its hand. Any new authored content for `arrival` or
  `seated` should read as the real Nika — that is what makes the
  recognition that follows hurt.

## Code anchors

- `game/world_state.py` — `ReunionStage` literal, `reunion_stage` field,
  `reunion_complete()`, and the coupled side effects in
  `enter_wrong_layer()` / `exit_wrong_layer()`.
- `game/actions/use.py` — the canonical stage handlers for `window`,
  `mug`, and `nika`. Where the prose lives.
- `game/map.py` — `_wrong_cabin_description` (stage-driven room text),
  movement guard blocking exit before `complete`, Wrong Outside pivot
  gated on `reunion_complete()`.
- `game/devtools/seed_saves.py` — seeds that pre-set `reunion_stage`
  for playtesting (`arrival`, `seated`, `complete`).
- Related mechanic docs:
  - `docs/game_mechanics/world-layers-mechanic.md` — how the layer flip
    enters the reunion and how the exit collapses it.
  - `docs/game_mechanics/wrongness-mechanic.md` — the Act III tells
    gated behind `complete`.
