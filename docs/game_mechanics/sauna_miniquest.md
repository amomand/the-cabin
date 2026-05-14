# Cabin Mini-Quest: The Sauna

## Premise

The sauna is a separate building, cedar-dark, with the stove in the
corner and the lake visible through the small window. The sauna beat is
the only moment in Act I that is unambiguously good — heat, stillness,
the place belonging to the part of Elli that loved it. It exists so the
Lyer has something specific to imitate later: the warmth of being held
by a familiar room.

Mechanically the beat is small. There is no precondition beyond being in
the sauna with the stove available. Story-wise it is the calm beat
before the bed, the voicemail, the camera. In playthrough order it can
fall anywhere in Act I.

---

## Game flow

### 1. Pre-use: the sauna waits

The sauna stove is a fixture in the sauna room. There is no pre-state
denial; `use sauna stove` fires the beat immediately when the player
reaches the room.

### 2. The beat fires

With `sauna_used == False`, `use sauna stove` runs the authored prose:

> "You feed the stove and wait. The stones heat slowly. The little room
> glows around you. Through the small window the lake shows between the
> trunks, a black plate under dusk. For the first time since arriving,
> the place belongs to the part of you that loved it."

The action sets `world_state["sauna_used"] = True` and emits a
`sauna_used` event.

### 3. Sauna already used: replay echo

Re-using the stove returns:

> "The stones are still warm. You don't need it again. The place has
> already done what it came to do."

No state change. Event: `use_sauna_again`.

---

## State flag

`WorldState.sauna_used: bool` (defaults `False`). Set in the beat above,
persisted across save/load via `world_state.py:239`.

Gates downstream:

- **None in production code.** `sauna_used` is currently a recorded
  beat: nothing keys off it for movement, parsing, or other gates. It
  is preserved across save/load so dev seeds and future quest logic can
  read it (`game/devtools/seed_saves.py:64` sets it for downstream
  seeds), but the engine does not consume it the way it consumes
  `voicemail_heard` / `footage_reviewed` / `first_morning`.

This is deliberate as authored: the sauna is the one Act I beat with no
mechanical cost or follow-up. Its job is to land emotionally, then sit
in the save state as a fact about the playthrough.

---

## Tells fired

None. The sauna is the cleanest beat in the game. No anomaly is
observed, no `log_tell()` call. The wrongness has not started leaking
through here.

---

## Code anchors

- `game/world_state.py:133` — `sauna_used: bool = False` field.
- `game/world_state.py:239` — JSON serialisation field list.
- `game/actions/use.py:115-134` — the `sauna stove` branch in
  `UseAction.execute`: the beat, the flag set, the already-used echo.
- `game/map.py:177-189` — the sauna `Room` definition; `sauna stove`
  placed in `items`.
- `game/devtools/seed_saves.py:64` — dev seeds set `ws.sauna_used =
  True` directly when jumping past Act I.
