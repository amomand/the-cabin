# 🔌 Cabin Mini-Quest: Restoring Power

## ❄️ Premise:
Player attempts to use cabin utilities (lights, tap, stove) but nothing works. They must restore power by going outside and interacting with the frozen fuse box. This event introduces early signs of the Lyer’s influence through unnatural cold and creeping dread.

---

## 🧩 Game Flow:

### 1. Inside Cabin: Pre-Power

- Player tries to interact:
  - "You flip the light switch. Nothing happens."
  - "The tap groans faintly. No water flows."
  - "The heater clicks once, then dies."

- Game hint:
  - "Maybe the fuse box outside needs checking."

---

### 2. Outside Cabin: Fuse Box Interaction

- On fuse box interaction:
  - "The cold here is sharper. Wrong, somehow."
  - "The fuse box door is frozen shut."
  - "You prise it open with stiff fingers, metal biting your skin."

- **Triggered eerie lore passage**:

    Something pressed at the edge of his awareness.

    Not sound. Not sight. Just… presence.

    The woods behind him were still. Silent. But a small, primal part of his brain whispered.

    He turned, scanning the treeline. Pines faded into grey mist. Nothing moved.

    He waited, holding breath he didn’t realise he’d taken. Snow creaked faintly beneath his boots. Still nothing.

- (Consider delivering the passage line-by-line with brief delays for pacing.)

---

### 3. Restoring Power

- Player flips the switch:
  - "You throw the switch. With a thunk, power hums faintly back to life inside the cabin."

- When re-entering the cabin:
  - "The lights flicker on. The tap gurgles. It's almost comforting — almost."

---

## 🧠 Implementation Notes:

- Add a `has_power` flag to game state
- Fuse box could be:
  - A `Room` (e.g. “Back of Cabin”)
  - Or an interactable `object` in the current room
- Make power state affect room/event behaviour
- Trigger presence text as a **one-time** timed event after the fuse is restored
