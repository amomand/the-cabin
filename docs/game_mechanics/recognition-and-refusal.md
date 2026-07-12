# Recognition & Refusal (Acts IV–V Mechanic)

## Overview

This is the endgame arc. After the reunion completes in Act III, three
linked beats turn the player's accumulating wrongness into a choice they
can act on. The arc spans the Act III pivot, the Act IV recognition, and
the Act V endings:

1. **Wrong Outside** — the **Act III pivot**. Elli steps out of the wrong
   cabin with Nika and sees the driveway is gone. The lie becomes
   spatially undeniable.
2. **Correction-turn (recognition)** — the **Act IV beat**. Elli watches
   Nika "return" from a pause with a turn that is too smooth. The
   knowing finishes itself.
3. **Refuse / Accept** — the **Act V endings**. At the cabin threshold,
   with the offer still in the air, Elli either walks away or steps
   back inside.

The act labels here match the comments in `world_state.py`, `map.py`,
`anomalies.py`, the file headers in `actions/refuse.py` /
`actions/accept.py`, and the dev seed `seed_act4_recognition`. New
recognition-path code should use the same labelling.

The mechanic exists so the recognition that lands feels paid for and so
the choice itself is bounded — Elli cannot refuse what she has not
recognised, and she cannot recognise without first having seen the
outside fail.

## State model

Three flags on `WorldState` track the arc, plus the ending literal:

| Field | Type | Meaning |
|-------|------|---------|
| `wrong_outside_seen` | `bool` (default `False`) | The driveway-is-gone pivot has fired. Reset by `exit_wrong_layer()`. |
| `recognition` | `bool` (default `False`) | The correction-turn beat has landed. Elli has finished the knowing. **Not** reset by `exit_wrong_layer()` — once she knows, she knows. |
| `ending` | `EndingState = "none" \| "accepted" \| "refused"` (plus `"escaped"` / `"stayed"`, reserved for the rewritten-canon arc, #141) | Which Act V choice landed, if any. Persisted across save/load. |

The fourth dependency is the wrongness log threshold —
`wrongness.threshold_met()` (currently `>= 3`) — see
`docs/game_mechanics/wrongness-mechanic.md`.

## The three beats

### 1. Wrong Outside pivot (`map.py:_wrong_outside_beat`)

**Where it fires:** in `Map.move()`, when Elli moves from `cabin_main` to
`cabin_clearing` with all of:
- `world_layer == "wrong"`
- `reunion_complete()` (reunion stage is `"complete"` or later)
- `wrong_outside_seen == False`

**What it does:** runs the `_wrong_outside_beat()` prose (Nika follows
Elli onto the threshold; the clearing is wrong; the driveway is gone; her
car is gone; the trees are ancient and too close; the sky is flat and
painted on). Nika is the one who names it: *"This isn't where I drove
to."* Sets `wrong_outside_seen = True`.

The beat fires **once per wrong-layer visit**. It is cleared by
`exit_wrong_layer()`, so a future replay of the wrong layer (currently
not reachable, but the model allows for it) would re-fire it.

This pivot does **not** set `recognition`. The Wrong Outside is when the
*world* becomes visibly wrong. Recognition is when *Nika* does.

### 2. Correction-turn / recognition (`map.py:_correction_turn_beat`)

**Where it fires:** in `Map.move()`, on entry to `old_woods` with:
- `world_layer == "wrong"`
- `recognition == False`

(Note: `wrong_outside_seen` is *not* a hard pre-condition for the
correction-turn in the move guard. In practice Elli only reaches
`old_woods` in the wrong layer via the wrong clearing, so the Wrong
Outside beat will already have fired — but the recognition beat itself
guards only on `recognition`.)

**What it does:** runs the `_correction_turn_beat()` prose (Nika stops in
a small clearing, held-still in a way that is not her stillness; Elli
calls her name; Nika "returns" with a smile that is right and a voice
that is right, but the *turn* is wrong — a correction, not a return).
Then:
- `log_tell(world_state, AnomalyID.CORRECTION_TURN)` — adds the
  definitive tell to the wrongness log.
- `world_state.recognition = True`.

This is the only place `recognition` is set in production code. (Dev
seeds in `seed_saves.py` set it directly for playtesting; nothing else
should.)

After recognition, the wrong `old_woods` description also echoes the
beat as a callback (`_wrong_old_woods_description`), so re-entering the
clearing replays the moment without re-firing the flag set.

### 3. Refuse / Accept (`actions/refuse.py`, `actions/accept.py`)

Both actions share the same gating structure. Each guard returns
stage-appropriate authored prose rather than a denial:

| Guard | Failure prose (refuse) | Failure prose (accept) |
|-------|------------------------|------------------------|
| Missing `recognition` **or** wrongness threshold not met | *"The word sits in your mouth, shapeless..."* | *"The thought comes wrapped in warmth, too soft to hold..."* |
| Not in the wrong layer (`is_wrong_layer()` false) | *"Nothing to refuse. Only the cabin, and the cold..."* | *"There is no offer now. Only the ordinary cabin..."* |
| Not at the offer threshold (`room_id != "cabin_clearing"`) | *"You try to make the word mean something, but the cabin is not in front of you..."* | *"The thought of staying finds no handle here..."* |

When all guards pass:
- Both call `ws.exit_wrong_layer()` (which collapses the reunion and
  clears `wrong_outside_seen` as documented in
  `world-layers-mechanic.md`).
- Both set `ws.ending` — `"refused"` or `"accepted"` respectively.
- Both emit a paired event (`wrong_layer_exited` plus an
  `ending_refused` / `ending_accepted` marker) and a state-change
  payload that mirrors the new layer and ending.
- Each ends with its own authored coda (the loop of clearings for
  refusal; the door closed from inside, then re-opened on the real
  morning, for acceptance).

`recognition` is **not** cleared by either ending. Once Elli knows,
that's permanent in the state.

## Why both flags are required

Refuse and Accept gate on `recognition AND wrongness.threshold_met()`.
Either alone is insufficient:

- **Tells without recognition** are just unease. The player has noticed
  things are off, but Nika is still Nika and the offered warmth is still
  warm. There is nothing yet to refuse.
- **Recognition without tells** should not be reachable by normal play.
  The correction-turn beat fires inside the wrong layer, and the wrong
  layer is only entered after the Act II climax, which itself requires
  three tells. The dual gate exists as a safety so a dev seed or a
  malformed save cannot put the player into a refusable state with no
  earned weight.

This is enforced in two places:
- The action handlers themselves (`refuse.py:32`, `accept.py:22`).
- The AI's `_act_v_offer_active()` predicate, which only signals the
  offer is "live" when `recognition AND world_layer == "wrong" AND
  ending == "none" AND room_id == "cabin_clearing" AND >= 3 tells`.

## Authoring guidance

### Recognition is a scene, not a flag flip

The CLAUDE.md anti-pattern "silent flag flips for narrative beats" was
written with this beat in mind. `world_state.recognition` is set
*inside* `_correction_turn_beat()`, alongside the prose that earns it.
Do not introduce a code path that flips `recognition` from an `on_enter`
callback, an ambient handler, or an item interaction. The knowing has to
land as the scene that holds it.

The same applies to `wrong_outside_seen` and to `ending`. None of these
should change outside of the authored beat that justifies the change.

### Pre-recognition denials are their own beats

Every guard in `refuse.py` and `accept.py` returns authored prose for
the failure case. None of them say "you can't" or surface a system
message. This is the canonical pattern for any future "too early"
denial in the game: the failure is a sensory moment about Elli's
incomplete understanding, not a rejection of the input.

If you add a new gate or change the conditions, the corresponding
failure prose must be authored in the same style.

### Endings live in the action handlers

Both `actions/refuse.py` and `actions/accept.py` carry the full ending
prose inline in the action's `ActionResult`. They are authored beats,
not AI-generated. Per `CLAUDE.md`: AI is for intent parsing in
story-critical scenes, not for rewriting them. If a player types
something the action can't parse, the parser routes through generic
fallbacks — never let the model paraphrase the ending.

### The offer threshold is fiction-shaped

Both endings are gated on `room_id == "cabin_clearing"`. This is
deliberate: the offer is the door, and the door is the threshold of the
cabin in the clearing. The same actions called from anywhere else in the
wrong layer narrate the absence of the door rather than firing the
ending. If you add new rooms to the wrong-layer path, do not extend the
threshold check casually — the choice is supposed to be located.

### Replay / reset semantics

`exit_wrong_layer()` (called by both endings, and available standalone)
clears `reunion_stage`, `wrong_outside_seen`, and `consent_given`. It does
**not** clear
`recognition` or `ending`. This is intentional: returning to the real
world after either ending is not amnesia. If a dev workflow needs to
reset the full arc to replay it, that's what dev seeds in
`seed_saves.py` are for — explicit, named, and limited to playtesting.

## Diegetic constraints

- The three flags (`wrong_outside_seen`, `recognition`, `ending`) are
  invisible to the player. No journal entry. No "Recognition: True"
  surface. The arc is felt, not displayed.
- Neither ending uses the word *Lyer*, neither names what was offered.
  The fiction works because the warmth is real and the refusal is a
  cost. Mechanics docs may name the Lyer (see `CLAUDE.md`); endings
  must not.
- The acceptance ending is not punitive. The cabin "groans" and the
  birches "lean toward the cabin," but the morning Elli wakes to is
  ordinary. The horror is consent, not damnation. New authored content
  around either ending must hold that line.

## Code anchors

- `game/world_state.py` — `EndingState` literal, `recognition`,
  `wrong_outside_seen`, `ending` fields; reset semantics in
  `exit_wrong_layer()` (clears `wrong_outside_seen`, not `recognition`).
- `game/map.py` — `_wrong_outside_beat`, `_correction_turn_beat`, and
  the move-time guards that fire each (around `Map.move()`).
- `game/actions/refuse.py` — Act V refusal: the threshold check,
  failure-mode prose, ending coda, `ws.ending = "refused"`.
- `game/actions/accept.py` — Act V acceptance: same shape, mirrored
  prose, `ws.ending = "accepted"`.
- `game/ai_interpreter.py` — `_act_v_offer_active()`: the AI's
  predicate for the live offer (mirrors the action handler's gates).
- `game/devtools/seed_saves.py` — `seed_act4_recognition` and adjacent
  seeds; the supported way to jump to a specific point in the arc.
- Related mechanic docs:
  - `docs/game_mechanics/world-layers-mechanic.md` — what
    `exit_wrong_layer()` does and what it does not reset.
  - `docs/game_mechanics/reunion-mechanic.md` — why `reunion_complete()`
    is the precondition for the Wrong Outside pivot.
  - `docs/game_mechanics/wrongness-mechanic.md` — the threshold gate
    shared with the action handlers.
