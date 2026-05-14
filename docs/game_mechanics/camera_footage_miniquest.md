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

> "Three feeds quiet. The northern one dead. You open the captured
> sequence.
> Five frames. A tall, narrow shape at the treeline. Closer in each
> frame. In the fourth, the trees behind it are not where they were in
> the third.
> The fifth frame is black. The feed died there."

The action sets `world_state["footage_reviewed"] = True` and emits a
`footage_reviewed` event.

### 3. Footage already reviewed: replay echo

Re-using the camera feed returns:

> "You scroll back to the same five frames. They have not changed. You
> already knew that. You look anyway."

No state change. Event: `use_footage_again`.

---

## State flag

`WorldState.footage_reviewed: bool` (defaults `False`). Set in the beat
above, persisted across save/load via `world_state.py:238`.

Gates downstream:

- **Bed beat / first morning.** `UseAction` for `bed` refuses to advance
  to `first_morning` unless both `voicemail_heard` and `footage_reviewed`
  are true. See `game/actions/use.py:155`. The narrated denial reads
  *"There's something you haven't done yet. The phone. The feeds. You
  get up again."* — i.e. the bed itself names the feeds as one of the
  two things Elli is avoiding.

`footage_reviewed` is the other half of that pair. Nothing else in the
codebase currently keys off it.

---

## Tells fired

None. The footage is the engine's first direct depiction of the Lyer,
but it is rendered as authored prose at the camera, not as a wrongness
anomaly. No `log_tell()` call. The Wrongness Log starts firing in Act II,
after `first_morning` — see `docs/game_mechanics/wrongness-mechanic.md`.

---

## Code anchors

- `game/world_state.py:132` — `footage_reviewed: bool = False` field.
- `game/world_state.py:238` — JSON serialisation field list.
- `game/actions/use.py:92-112` — the `camera feed` branch in
  `UseAction.execute`: the beat, the flag set, the already-reviewed echo.
- `game/actions/use.py:155` — the bed beat's prerequisite check that
  reads `footage_reviewed`.
- `game/map.py:141` — `camera feed` placed in the konttori room
  alongside the circuit breaker.
- `game/devtools/seed_saves.py:63` — dev seeds set
  `ws.footage_reviewed = True` directly when jumping past Act I.
