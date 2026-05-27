# Cabin Mini-Quest: The Bed and the First Morning

## Premise

The bedroom holds a single bed under heavy covers. Sleeping in it ends
Act I and opens Act II — `first_morning` is the gate that turns the
woods around the cabin from ordinary forest into the place where tells
begin to fire. The bed is also the most heavily guarded beat in Act I:
it refuses to advance unless the fire is lit, the voicemail has been
heard, and the camera footage has been reviewed.

This is by design. The morning Elli wakes to is the morning the
Wrongness Log starts filling. The engine does not let her get there
until she has done the three small things that authorise the night
before — settle the cabin, hear the warning, see the tape.

---

## Game flow

### 1. Pre-fire: the bed refuses the cold

If the player uses the bed before `fire_lit`, the action returns:

> "The bed is cold. The cabin is colder. Build a fire first, or you'll
> lie awake all night listening to the house remember itself."

No flag change. Event: `use_bed_too_cold`.

### 2. Fire lit, but the phone and feeds unread

With `fire_lit == True` but either `voicemail_heard` or
`footage_reviewed` still false:

> "You sit on the edge of the bed and stop. There's something you
> haven't done yet. The phone. The feeds. You get up again."

No flag change. Event: `use_bed_unfinished`. This is the narrated
prerequisite: the bed beat itself names the two missing tasks rather
than emitting any kind of system denial.

### 3. All preconditions met: the beat fires

With `fire_lit`, `voicemail_heard`, and `footage_reviewed` all true,
and `first_morning == False`, `use bed` runs the authored prose:

> "You lie down under the heavy covers. Wine warmth. The smell of dry
> wood in the boards. You lie awake longer than you expected. The
> isolation is not hostile. It is absolute.
> You remember the scraping sound from when you were small, and the way
> your parents explained it away. You tell yourself you'll check the
> northern edge in daylight.
> Sleep comes. Then, later, the silence of the first morning."

The action sets `world_state["first_morning"] = True` and emits a
`first_morning` event.

### 4. First morning already landed: replay echo

Re-using the bed returns:

> "You look at the bed. Not now. The morning is waiting outside, and so
> is something else."

No state change. Event: `use_bed_again`.

---

## State flag

`WorldState.first_morning: bool` (defaults `False`). Set in the beat
above, persisted across save/load via `world_state.py:240`.

This is the most consequential Act I gate. It does three structural
things downstream:

1. **Act II ambient tells become observable.** The cabin grounds, wood
   track, and old woods all use `description_fn` and `on_enter`
   handlers that gate their wrongness prose and `log_tell()` calls on
   `world_state.first_morning`. Before the first morning these rooms
   render the base description; after, fox tracks, the hare, and the
   stone formations appear and log into the Wrongness Log (see
   `Map.__init__` room setup together with `_grounds_description`,
   `_on_enter_grounds`, `_wood_track_description`,
   `_on_enter_wood_track`, `_old_woods_description`,
   `_on_enter_old_woods` in `game/map.py`).
2. **The Act II Lyer-encounter trigger arms.** In `Map.move()`, any
   attempt to leave `old_woods` requires `first_morning` (and three
   tells, and `not lyer_encountered`, and real layer) to fire the Lyer
   beat instead of the move (see `Map.move` in `game/map.py`).
3. **Implicitly authorises the rest of the arc.** Because the bed beat
   demands the voicemail and the footage to advance, `first_morning ==
   True` in a save state guarantees those two preceding beats have also
   landed.

---

## Tells fired

None at the beat itself. `log_tell()` is not called inside the bed
action — the morning is the gate, not the tell.

The tells that *follow* this gate (firing in Act II rooms once
`first_morning` is set):

- `AnomalyID.FOX_TRACKS.value` — logged on entry to the cabin grounds
  in `Map._on_enter_grounds`.
- `AnomalyID.HARE.value` — logged on entry to the wood track in
  `Map._on_enter_wood_track`.
- `AnomalyID.STONE_FORMATIONS.value` — logged on entry to the old woods
  in the real layer in `Map._on_enter_old_woods`.

These three are the canonical "threshold of three" that arms the Lyer
encounter — see `docs/game_mechanics/wrongness-mechanic.md`.

---

## Code anchors

- `game/world_state.py:134` — `first_morning: bool = False` field.
- `game/world_state.py:240` — JSON serialisation field list.
- `game/actions/use.py:137-175` — the `bed` branch in
  `UseAction.execute`: the already-landed echo, the cold-bed denial,
  the phone-and-feeds denial, the beat itself that sets the flag.
- `game/map.py` `Map.move` — the Act II Lyer-encounter guard that reads
  `first_morning` together with the wrongness threshold.
- `game/map.py` `Map.__init__` and helper callables
  (`_grounds_description`, `_on_enter_grounds`,
  `_wood_track_description`, `_on_enter_wood_track`,
  `_old_woods_description`, `_on_enter_old_woods`) — Act II description
  and `on_enter` handlers that gate tells on `first_morning`; the route
  now bends through the lake and shoreline before reaching the old
  woods.
- `game/map.py:148-160` — the bedroom `Room` and the `bed` item.
- `game/devtools/seed_saves.py:65` — dev seeds set `ws.first_morning =
  True` directly when jumping into Act II or later.
