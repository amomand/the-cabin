# Cabin Mini-Quest: The Bed and the First Morning

## Premise

The bedroom holds a single bed under heavy covers. Sleeping in it ends
Act I and opens Act II — `first_morning` is the gate that turns the
woods around the cabin from ordinary forest into the place where tells
begin to fire. The bed is also the most heavily guarded beat in Act I:
it refuses to advance unless the fire is lit, the voicemail has been
heard, the camera footage has been reviewed, and the sauna has been used.

This is by design. The morning Elli wakes to is the morning the
Wrongness Log starts filling. The engine does not let her get there
until she has done the four small things that authorise the night
before: settle the cabin, hear the warning, see the tape, and let the sauna
briefly close the distance to the place.

---

## Game flow

### 1. Pre-fire: the bed refuses the cold

If the player uses the bed before `fire_lit`, the action returns:

> "The blankets are cold through. Without a fire they will not lose it."

No flag change. Event: `use_bed_too_cold`.

### 2. Fire lit, but an evening beat remains unfinished

With `fire_lit == True` but any of `voicemail_heard`,
`footage_reviewed`, or `sauna_used` still false, the response is composed
from the missing beats. For example:

> "You sit on the edge of the bed. Nika's message waits on the phone.
> The sauna is still cold above the lake. You get up."

No flag change. Event: `use_bed_unfinished`. This is the narrated
prerequisite: the bed beat names only what still waits rather than
emitting any kind of system denial.

### 3. All preconditions met: the beat fires

With `fire_lit`, `voicemail_heard`, `footage_reviewed`, and `sauna_used`
all true,
and `first_morning == False`, `use bed` runs the authored prose:

> "You eat bread and packet soup at the square table, pour one glass of
> wine, and drink it. You cork the bottle on the counter, the empty glass
> beside it.
> Under the heavy covers, the isolation becomes total: the nearest lit
> window forty minutes south, no signal unless you hold the phone to the
> glass, the dark going on over the lake and bog.
> The fire ticks in the other room. You think of the empty hook and the
> scraping under the boards, then set yourself the morning's work: the
> northern camera in daylight, battery, moisture, board, in that order.
> You sleep better than you expect. You wake into silence. Then a log
> shifts in the hearth and puts sound back in the room. Ten past eight and
> the window is still black."

The action sets `world_state["first_morning"] = True` and emits a
`first_morning` event.

### 4. First morning already landed: replay echo

Re-using the bed returns:

> "You have slept enough. The morning waits outside."

No state change. Event: `use_bed_again`.

---

## State flag

`WorldState.first_morning: bool` (defaults `False`). Set in the beat
above, persisted across save/load via `world_state.py:240`.

This is the most consequential Act I gate. It does three structural
things downstream:

1. **Act II attention tells become observable.** The cabin grounds,
   wood track, and old woods all use `description_fn` handlers that cue
   wrongness once `world_state.first_morning` is true. The full tells
   and `log_tell()` calls fire from `Map.observe_current_room()` when
   the player looks in the three Act II tell rooms; `listen` is also a
   valid attention path for the hare on the wood track. Before the first
   morning these rooms render the base description.
2. **The Act II Lyer-encounter trigger arms.** In `Map.move()`, any
   attempt to leave `old_woods` requires `first_morning` (and three
   tells, and `not lyer_encountered`, and real layer) to fire the Lyer
   beat instead of the move (see `Map.move` in `game/map.py`).
3. **Implicitly authorises the rest of the arc.** Because the bed beat
   demands fire, voicemail, footage, and sauna to advance, `first_morning ==
   True` in a naturally reached save state guarantees all four preceding
   beats have landed.

---

## Tells fired

None at the beat itself. `log_tell()` is not called inside the bed
action — the morning is the gate, not the tell.

The tells that *follow* this gate (observable in Act II rooms once
`first_morning` is set):

- `AnomalyID.FOX_TRACKS.value` — logged by `look` in the cabin
  grounds.
- `AnomalyID.HARE.value` — logged by `look` or `listen` on the wood
  track.
- `AnomalyID.STONE_FORMATIONS.value` — logged by `look` in the old
  woods in the real layer.

These three are the canonical "threshold of three" that arms the Lyer
encounter — see `docs/game_mechanics/wrongness-mechanic.md`.

---

## Code anchors

- `game/world_state.py` — `first_morning: bool = False` field and JSON
  serialisation field list.
- `game/actions/use.py` — the `bed` branch in
  `UseAction.execute`: the already-landed echo, the cold-bed denial,
  the composed unfinished-beat denial, and the beat itself that sets the flag.
- `game/map.py` `Map.move` — the Act II Lyer-encounter guard that reads
  `first_morning` together with the wrongness threshold.
- `game/map.py` `Map.__init__`, `Map.observe_current_room`, and helper
  callables (`_grounds_description`, `_wood_track_description`,
  `_old_woods_description`) — Act II entry cues and attention-gated
  tells; the route now bends through the lake and shoreline before
  reaching the old woods.
- `game/map.py` — the bedroom `Room` and the `bed` item.
- `game/devtools/seed_saves.py` — dev seeds set `ws.first_morning =
  True` directly when jumping into Act II or later.
