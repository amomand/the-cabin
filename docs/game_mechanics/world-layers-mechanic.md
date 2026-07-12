# World Layers Mechanic

## Overview

The world has two layers: `real` and `wrong`. The same locations exist in
both, with the same rooms in the same places, but the wrong layer is the
Lyer's arrangement of them — the cabin made out of Elli's memory of the
cabin, not the cabin itself. The mechanic is small in code and enormous in
implication: every room can ship a second face that the engine swaps in when
the world flips.

Acts II–V depend on this. The Act II climax flips Elli into the wrong layer;
the false-cabin night plays out inside it; after the dawn refusal she walks
out on foot, and the final southward step flips her back. The mechanic
exists to make all of that legible to the code without sacrificing the
fiction's central trick — that the cabin **is** the cabin until it isn't.

## State model

`WorldState.world_layer` is a `Literal["real", "wrong"]` and defaults to
`"real"`. It is validated on construction and round-trips through save/load.
Three helpers wrap it:

| Method | Effect |
|--------|--------|
| `enter_wrong_layer()` | Sets `world_layer = "wrong"`. If `reunion_stage == "none"`, also advances it to `"arrival"` (Nika is on her feet the moment Elli crashes through the door). |
| `exit_wrong_layer()` | Sets `world_layer = "real"`. Resets `reunion_stage` to `"none"`, and `wrong_outside_seen` and `consent_given` to `False`. The refusal dissolves the reunion along with the wrong cabin. |
| `is_wrong_layer()` | Convenience predicate used by rooms, actions, and AI context. |

Always go through the helpers, never assign `world_layer` directly. The
helpers carry the coupled side effects (reunion stage, `wrong_outside_seen`)
that keep the story state coherent.

## Transitions

There are exactly two scripted transitions in the game today.

### Real → Wrong: the Act II climax (`map.py:_trigger_lyer_encounter`)

Triggered when Elli tries to leave `old_woods` after `first_morning` with
three or more wrongness tells logged and the Lyer not yet encountered.
The handler:

1. Sets `lyer_encountered = True`.
2. Bleeds fear (+40, clamped to 99) and health (-20, clamped to 1) from the
   collision with the tree. Clamps deliberately stay short of the death
   thresholds — this beat must not end the run mid-scene.
3. Calls `enter_wrong_layer()`. The reunion implicitly begins at
   `"arrival"`.
4. Teleports Elli to `cabin_main` and marks the room as visited (she "knows"
   this cabin, which is the point).
5. Fires the room's `on_enter` and returns the authored climax prose.

### Wrong → Real: the walk out (`map.py:_arrive_home`)

The refusal (`actions/refuse.py`) does **not** exit the layer — it sets
`ending = "escaped"` and stops the pretence, and Elli walks out on foot:
`out` to the black clearing, `south` to the indifferent woods, and a final
`south` that fires `_arrive_home`. That handler calls `exit_wrong_layer()`
(resetting the reunion stage, `wrong_outside_seen`, and `consent_given`),
teleports her to the real `cabin_grounds_main`, and sets
`coda_stage = "home"`.

The stayed ending (`actions/accept.py`) never exits the layer at all. She
drinks the coffee and the run closes there (`game/ending.py`). The wrong
cabin is a place you leave on foot or not at all.

## How rooms render per layer

Rooms accept three wrong-layer parameters (`game/room.py`):

| Field | Purpose |
|-------|---------|
| `wrong_description` | Static overlay string used in place of the real description when the layer is wrong. |
| `wrong_description_fn` | Callable `(player, world_state, base) -> str` for layer-aware composition. Receives the wrong (or real, as fallback) base text and may compose around it. |
| `wrong_exits` | Replacement exits map. If set, the room's exits in the wrong layer differ from those in the real layer. |

`Room.get_description()` checks `is_wrong_layer()` and, if any wrong-layer
overlay exists, uses it. `Room.effective_exits()` does the same for
navigation.

The production example to learn from is `_wrong_cabin_description` in
`map.py`: it composes by `reunion_stage` across the whole false-cabin night
(arrival, tended, seated, complete, consented, bedded/night, dawn), surfaces
logged tells and night seams as callbacks, and switches to the stopped-room
description once `ending == "escaped"`.

A room only needs an overlay if it should look or behave differently when
the layer flips. Most rooms in the real layer are never visited in the
wrong layer and need nothing. The rooms that carry overlays today are
`cabin_clearing`, `cabin_main`, and `wood_track` — together they cover the
false cabin and the walk-out route between the Act II climax and the coda.

## AI context

`game/ai_context.py` filters which room items the AI is allowed to treat as
present, based on the layer. `WRONG_LAYER_ONLY_ROOM_ITEMS` lists items that
must not be perceivable in the real layer — currently `{"window", "mug",
"nika", "mattress", "tins"}`. The AI sees the full item list in the wrong
layer and the filtered list in the real layer.

This is how the wrong cabin can hold a mug and a Nika the real cabin cannot.
If you add an item that should only exist on one side of the flip, add it
to this set.

The AI's world-flag payload also surfaces `world_layer` so the model can
condition tone on the layer when authored prose is not driving the beat.

## Interaction with other systems

- **Wrongness log.** The evening tells (`FROST_WOOD_GRAIN`,
  `KNUCKLES_BIRCH`, `DELAYED_SMILE`) and the night seams only fire inside
  the wrong layer, gated by stage. See
  `docs/game_mechanics/wrongness-mechanic.md`.
- **Reunion stage.** `enter_wrong_layer()` advances the reunion to
  `"arrival"` if not already started; `exit_wrong_layer()` collapses it
  back to `"none"`. The stages are only meaningful inside the wrong layer.
- **Movement in `cabin_main`.** In the wrong layer, the door holds Elli
  all night: turned back to the chair before the reunion lands, the
  consent beat on the first `out` after it, authored denials until the
  dawn choice, and the walk out only after the refusal. The guards in
  `map.move()` enforce this — see `map.py` near the `is_wrong_layer()`
  checks.
- **Consent.** The first `out` at stage `complete` fires the consent-door
  beat and sets `consent_given` without moving her. This replaced the
  earlier wrong-outside pivot (`wrong_outside_seen` remains as a legacy
  field for save compatibility).

## Authoring guidance

### Narrate transitions. Never flip silently.

The helpers themselves are pure state mutations — they do not return or
emit prose. Authored prose for each transition lives in the **caller**:
`_trigger_lyer_encounter` in `map.py` narrates the Act II run, collision,
and threshold; `_arrive_home` in `map.py` narrates the end of the walk out
and calls `exit_wrong_layer()` inline as part of that authored beat.

Do not introduce a third transition that calls `enter_wrong_layer()` or
`exit_wrong_layer()` from an `on_enter` callback or an ambient handler
without a paired authored beat — that's the "silent flag flips for
narrative beats" anti-pattern in `CLAUDE.md`. If a new layer transition
is needed, the caller must own the prose. The fiction has to land at the
moment the world changes.

### Adding a wrong-layer overlay to a room

1. Decide whether the overlay is static (`wrong_description`) or composed
   (`wrong_description_fn`). Use a function whenever the overlay depends on
   `reunion_stage`, accumulated tells, or any other state.
2. If the room's exits differ in the wrong layer, pass `wrong_exits`.
3. If new wrong-only items appear in the room, list their names in
   `WRONG_LAYER_ONLY_ROOM_ITEMS` so the AI cannot perceive them in the
   real layer.
4. If the wrong layer surfaces previously-logged tells, gate them with
   `world_state.wrongness.has(AnomalyID.X.value)` so they only appear if
   the player has actually seen them — same pattern as
   `_wrong_cabin_description`.

### Authored prose, not AI prose

Both transitions and the wrong cabin's stage-by-stage descriptions are
authored beats. AI flavour does not write the cabin into the wrong layer.
Per `CLAUDE.md`: AI is for intent parsing in story-critical scenes, not for
rewriting them.

## Code anchors

- `game/world_state.py` — `WorldLayer`, `world_layer` field, validation,
  `enter_wrong_layer()`, `exit_wrong_layer()`, `is_wrong_layer()`,
  JSON serialisation.
- `game/room.py` — `wrong_description`, `wrong_description_fn`,
  `wrong_exits`, layer-aware `get_description()` and `effective_exits()`.
- `game/map.py` — `_trigger_lyer_encounter` (real → wrong),
  `_wrong_cabin_description` (the false-cabin night), the in-cabin
  movement guards, `_consent_door_beat`, the walk-out beats, and
  `_arrive_home` (wrong → real).
- `game/actions/refuse.py`, `game/actions/accept.py` — the dawn endings.
  Neither exits the layer directly: the escape leaves on foot, the stayed
  ending never leaves.
- `game/ai_context.py` — `WRONG_LAYER_ONLY_ROOM_ITEMS` and
  `visible_room_item_names()`.
- `game/ai_interpreter.py` — surfaces `world_layer` in the AI's world
  flags; used as part of the refusal-readiness check.
- `game/devtools/seed_saves.py` — seeds that pre-enter the wrong layer
  for playtesting.
