# Cabin Mini-Quest: The Camera Feeds

## Premise

The konttori (office) holds the camera feed monitor. Three perimeter feeds
should be live; one — the northern one — is dead. Among the saved footage
is a five-frame sequence captured shortly before the feed died. Elli has
to sit down with it. This is the Act I beat that introduces the Lyer
visually, at one remove, before Elli has any language for what she's
looking at.

The Lyer is on the tape. It is moving. The trees in the fourth frame are
not where they were in the third. Then the feed dies.

---

## Game flow

### 1. Pre-review: the monitor is just a monitor

In the konttori, the camera feed item is present but unread. There is no
pre-state denial — the player can `use camera feed` whenever they reach
the konttori. The action fires the beat immediately.

### 2. The beat fires

With `footage_reviewed == False`, `use camera feed` runs the authored
prose:

> "Three feeds show frost and stillness. The northern one is dead. You
> open the saved sequence from five weeks ago.
> Five frames. In the first, a tall, narrow shape stands at the treeline
> and the forked birch is at the right edge. By the fourth, the shape is
> closer and the birch has moved left of centre. The ground beneath it is
> unmarked.
> Frame five is black."

The action sets `world_state["footage_reviewed"] = True` and emits a
`footage_reviewed` event.

### 3. Footage already reviewed: replay echo

Re-using the camera feed returns:

> "You open the older five frames again. The forked birch is still at the right
> edge, then left of centre. You look until your thumb aches."

No state change. Event: `use_footage_again`.

---

## State flag

`WorldState.footage_reviewed: bool` (defaults `False`). Set in the beat
above, persisted across save/load via `world_state.py:238`.

Gates downstream:

- **Bed beat / first morning.** `UseAction` for `bed` refuses to advance
  to `first_morning` unless `voicemail_heard`, `footage_reviewed`, and
  `sauna_used` are all true. The narrated denial names the dead northern
  feed only while it remains unread.

Nothing else in the codebase currently keys off `footage_reviewed`.

---

## Tells fired

None. The footage is the engine's first direct depiction of the Lyer,
but it is rendered as authored prose at the camera, not as a wrongness
anomaly. No `log_tell()` call. The Wrongness Log starts firing in Act II,
after `first_morning` — see `docs/game_mechanics/wrongness-mechanic.md`.

---

## Code anchors

- `game/world_state.py` — `footage_reviewed: bool = False` field and
  JSON serialisation field list.
- `game/actions/use_handlers/act_one.py` — the `camera feed` handler: the
  beat, the flag set, the already-reviewed echo.
- `game/actions/use_handlers/act_one.py` — the bed beat's prerequisite check that
  reads `footage_reviewed`.
- `game/map.py` — `camera feed` placed on the desk in the konttori room.
- `game/devtools/seed_saves.py` — dev seeds set
  `ws.footage_reviewed = True` directly when jumping past Act I.
