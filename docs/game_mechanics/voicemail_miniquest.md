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

> "You pull out the phone, then stop. Not yet. You're still in coat and
> cold. Settle the cabin first."

No flag is set. The action emits `use_phone_too_early`.

### 2. Fire lit, voicemail not yet heard: the beat fires

With `fire_lit == True` and `voicemail_heard == False`, `use phone` plays
Nika's voicemail. The authored prose:

> You open the voicemail. Nika's voice. Terse, strained, not hers.
> "Elli. It's me. You need to come home."
> "Something's wrong with the cabin. I don't know what."
> "Don't go up on your own. Wait."
> "It's lying out there."
> You play it twice. The word "wait" hangs in the room.

The action then sets `world_state["voicemail_heard"] = True` and emits a
`voicemail_heard` event.

### 3. Voicemail already heard: replay echo

Re-using the phone returns:

> "You hold the phone a moment longer than you need to. Nika's voicemail
> sits there, already heard, already refusing to go quiet."

No state change. Event: `use_phone_again`.

---

## State flag

`WorldState.voicemail_heard: bool` (defaults `False`). Set in the beat
above, persisted across save/load via `world_state.py:237`.

Gates downstream:

- **Bed beat / first morning.** `UseAction` for `bed` refuses to advance
  to the `first_morning` beat unless both `voicemail_heard` and
  `footage_reviewed` are true. The narrated denial is *"You sit on the
  edge of the bed and stop. There's something you haven't done yet. The
  phone. The feeds. You get up again."* (`game/actions/use.py:157`).

`voicemail_heard` is one half of the pair the bed beat checks. Nothing
else in the codebase currently keys off it.

---

## Tells fired

None. No `log_tell()` call. The voicemail is a story beat, not a
wrongness anomaly — Nika's warning is real, not a Lyer-shaped tell.

---

## Code anchors

- `game/world_state.py:131` — `voicemail_heard: bool = False` field.
- `game/world_state.py:237` — JSON serialisation field list.
- `game/actions/use.py:60-91` — the `phone` branch in `UseAction.execute`:
  the pre-fire refusal, the voicemail beat that sets the flag, the
  already-heard echo.
- `game/actions/use.py:157` — the bed beat's prerequisite check that
  reads `voicemail_heard`.
- `game/map.py:107` — phone placed in `cabin_main`.
- `game/devtools/seed_saves.py:62` — dev seeds set `ws.voicemail_heard
  = True` directly when jumping past Act I.
