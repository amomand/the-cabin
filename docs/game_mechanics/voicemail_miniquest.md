# Cabin Mini-Quest: Nika's Voicemail

## Premise

Elli is inside the cabin, in coat and cold, still settling. The phone is in
her inventory but she will not check it yet — there's a sequence to landing
inside the cabin, and the voicemail is the second beat. The fire has to be
lit first. Only then does she let herself listen.

This is the Act I beat that puts Nika's voice in the room before Nika is.
Everything later — the wrong cabin, the reunion, the knowing — references
the warning Elli ignored here, and the refusal completes it: "She told me
one more thing. On the message."

---

## Game flow

### 1. Pre-fire: the phone refuses itself

If the player uses the phone before `fire_lit`, Elli stops her own hand:

> "You take out the phone, but your fingers are stiff on the case. The
> cold room comes first."

No flag is set. The action emits `use_phone_too_early`.

### 2. Fire lit, voicemail not yet heard: the beat fires

With `fire_lit == True` and `voicemail_heard == False`, `use phone` plays
Nika's voicemail. The authored prose:

> You play Nika's message again. Eleven days old, every word waiting where
> you left it.
> "Elli. It's me. You need to come home. Something's wrong with the cabin.
> I don't know what. Don't go up on your own. Wait. It's... it's lying out
> there."
> The pause before the last line is the worst part. Nika does not pause.

The action then sets `world_state["voicemail_heard"] = True` and emits a
`voicemail_heard` event.

### 3. Voicemail already heard: replay echo

Re-using the phone returns:

> "You do not play the message again. You can hear the pause without it."

No state change. Event: `use_phone_again`.

---

## State flag

`WorldState.voicemail_heard: bool` (defaults `False`). Set in the beat
above, persisted across save/load via `world_state.py:237`.

Gates downstream:

- **Bed beat / first morning.** `UseAction` for `bed` refuses to advance
  to the `first_morning` beat unless `voicemail_heard`,
  `footage_reviewed`, and `sauna_used` are all true. Its narrated denial
  names only the beats that remain unfinished.

Nothing else in the codebase currently keys off `voicemail_heard`.

---

## Tells fired

None. No `log_tell()` call. The voicemail is a story beat, not a
wrongness anomaly — Nika's warning is real, not a Lyer-shaped tell.

---

## Code anchors

- `game/world_state.py` — `voicemail_heard: bool = False` field and
  JSON serialisation field list.
- `game/actions/use.py` — the `phone` branch in `UseAction.execute`:
  the pre-fire refusal, the voicemail beat that sets the flag, the
  already-heard echo.
- `game/actions/use.py` — the bed beat's prerequisite check that
  reads `voicemail_heard`.
- `game/map.py` — phone placed in `cabin_main`.
- `game/devtools/seed_saves.py` — dev seeds set `ws.voicemail_heard
  = True` directly when jumping past Act I.
