
# ⚙️ Game Mechanics – *The Cabin*

A survival horror text adventure grounded in realism and creeping dread.  
You are not a hero. You are just trying to make it through.

---

## 🎭 Design Philosophy: Atmospheric Immersion

**Core Principle:** Leverage human psychology and natural behavior to create immersive experiences without explicit instruction.

**Key Tenets:**
- **Uncertainty as Atmosphere:** Create moments where players naturally pause, think, and tentatively proceed - this mirrors the cautious, fearful behavior that survival horror wants to evoke.
- **Psychological Engagement:** Use silence, pauses, and lack of guidance to force players to engage with the unsettling atmosphere rather than just reading instructions.
- **Narrative Integration:** Every element should serve both function and atmosphere. Text isn't just flavor - it's setting up stakes, backstory, and tone without exposition dumps.
- **Technical Elegance:** Simple changes that leverage human psychology are more effective than complex systems. Players will naturally figure out what to do, but that moment of uncertainty creates the perfect mood.
- **Genre Authenticity:** Every interaction should feel like classic survival horror - brief, unsettling moments that set tone before dropping players into the world.

**Example:** The game intro displays dark, spooky text without instruction, creating immediate tension. Players naturally pause, read, then tentatively press a key - this mimics the cautious behavior the game wants to evoke throughout the experience.

---

## 🫀 Health

- **Represents:** Physical condition. Injuries, illness, exhaustion.
- **Impacts:**
  - Affects mobility, vision clarity, and stamina.
  - Low health can cause blackouts, hallucinations, or death.
- **Sources of Damage:**
  - Falls, cuts, cold exposure, wild animals, minions.
  - Attempting tasks while terrified (e.g. fleeing blindly through woods).
- **Recovery:**
  - Rest (safe sleep).
  - Medical items (bandages, antiseptic, painkillers).
  - Sauna may offer partial recovery — if you dare to use it.

---

## 🧠 Fear

- **Represents:** Mental/emotional stability.
- **Impacts:**
  - High fear makes actions harder or more likely to fail (e.g. fumble key, misread map, misfire weapon).
  - Dialogue options may change or become unavailable.
  - Hallucinations or unreliable narration.
- **Triggers:**
  - Supernatural events.
  - Darkness, isolation, certain locations.
  - Direct encounters with the Lyer or its minions.
- **Recovery:**
  - Light, warmth, and company.
  - Reading familiar books, hearing music, finding keepsakes.
  - Small victories (surviving an encounter, solving a mystery).

---

## 👁️ The Lyer

- **Rules:**
  - Encountering the Lyer too early = game over.
  - Presence causes max fear spike instantly.
  - The closer you are, the colder and more silent the world becomes.
- **Strategy:**
  - Avoid direct contact until prepared.
  - Clues will hint at its presence before it arrives.
  - “Level up” courage by overcoming lesser minions and facing personal fears.

---

## 👤 Minions / Echoes

- **Description:** Lesser manifestations of dread, tied to place, memory, or deception.
- **Function:**
  - Act as obstacles that test fear and decision-making.
  - Defeating or surviving them increases courage and player resolve.
  - Some might be avoidable; others must be faced.

---

## 🎒 Inventory

- **System:**
  - Limited space (weight or slots — TBD).
  - Prioritise: food, tools, weapons, notes, keepsakes.
- **Features:**
  - Some items degrade over time (flashlight batteries, painkillers).
  - Items can be lost if fleeing or panicking.
  - Certain items help manage fear (e.g. a childhood photo, a pocketknife, a thermos of hot coffee).
- **Interaction:**
  - Simple text input (e.g. `> check bag`, `> drink coffee`, `> drop map`).

---

## 🕯️ Light and Darkness

**Status:** Partially implemented — light sources and the cabin's lit/dark state are wired through gameplay; battery/wind reliability and darkness-only event gating are aspirational.

- **What's implemented today:**
  - **The hearth.** `LightAction` (and the `use matches` path in `actions/use.py`) requires both `matches` and `firewood` to set `world_state.fire_lit = True`. Without firewood the match burns out; without matches the firewood sits dark. Lighting the fire is an Act I gate for `use bed`.
  - **Mains power.** `cabin_main` exposes a `light switch` item. Flipping it before the circuit breaker has been used returns the authored "the cabin remains dark" feedback and emits `use_light_switch_no_power`. After `use circuit breaker` sets `world_state.has_power = True`, the switch turns on and the cabin's room description shifts to *"The overhead light hums faintly."*
  - **Lit / dark cabin description.** `map.py` swaps the cabin's room description based on three states: fire-lit, mains-lit, or *"The cabin is dark. Cold seeps through the floorboards."*
  - **Darkness as a fear trigger.** Throwing an item outdoors with no specific target emits `thrown_into_darkness`, which the engine routes through the fear system. This is the only place "darkness" is currently a mechanic and not a description.
- **Sources of Light:**
  - Matches + firewood → hearth fire (real items, real flag).
  - Circuit breaker + light switch → mains lighting (real items, real flag).
  - Moonlight / lake light / sky — narrative only; no item.
- **Aspirational (not yet implemented):**
  - Flashlights, batteries, candles, lanterns. No item of these names exists in `game/item.py`.
  - Light source reliability — batteries dying, wind extinguishing a match outdoors, fire burning down. The `fire_lit` flag does not decay.
  - Darkness-gated events ("only triggers in full dark", "needed to avoid minions", revealing hidden text). Room visibility is uniform; descriptions vary, content does not.
- **Authoring note:** the Lyer is described as cold and as muting light around it (*"a wall of cold against your face. The silence becomes absolute"* in `map.py`). That is authored prose, not a light-radius system.

---

## 🧭 Exploration

- **World Structure:**
  - Procedurally generated grid or graph of locations (cabin, forest, lake, ruins, etc.)
  - Some areas only accessible after certain events or item finds.
- **Navigation:**
  - Map may be incomplete or hand-drawn.
  - Weather or fear may alter perception of routes.
- **Secrets:**
  - Hidden paths, buried objects, locked cellars.
  - Environmental storytelling layered in.

---

## 📝 Journal / Memory

**Status:** Aspirational — there is no in-game journal today. The nearest existing system is the **Wrongness Log**, which is deliberately invisible and is not a journal.

- **What exists today:**
  - `WrongnessLog` on `WorldState` accumulates observed anomalies via `log_tell()`. See `docs/game_mechanics/wrongness-mechanic.md`. The log is surfaced to the player only through prose at the moment of observation; it is never opened, listed, or named. There is no `journal` command, no menu, no on-screen counter.
  - **Memory Fragments** (see the section below) are non-interactive narrative beats keyed to locations and events. They are read once when they fire. They are not stored or replayable in any current implementation.
- **Aspirational mechanic:**
  - A diegetic journal that Elli writes to — discoveries, dreams, fragments of thought — that the player can re-read.
  - **Unreliable entries** at high fear or after supernatural events. Words drift; a page Elli remembers writing is blank or rewritten.
  - **Entries that appear without being written** — a page in Elli's hand that isn't hers, paragraphs in the wrong tense, a name she doesn't recognise.
- **If implemented, anti-patterns to avoid:**
  - Surfacing `WrongnessLog` as a journal page titled *"Wrongness."* The wrongness mechanic must remain beneath the surface; a journal would need its own state and its own authored content.
  - Using a journal as a hint system. Per the diegetic immersion rule, the game does not explain its mechanics back to the player. A journal must read like Elli's own writing, not a quest log.
- **Cross-reference:** `docs/game_mechanics/wrongness-mechanic.md` is explicit that tells are *not* clues and the log is *not* a journal. Any journal mechanic added later should preserve that boundary.

---

## 🧊 Cold

**Status:** Aspirational as a stat-bearing system. The word "cold" carries enormous narrative weight today, but no temperature value, exposure timer, or hypothermia path is implemented. Two real flags — `fire_lit` and `sauna_used` — anchor the warmth side of the fiction.

- **What's implemented today:**
  - **`fire_lit` as warmth gate.** Without `fire_lit`, `use bed` returns *"The bed is cold. The cabin is colder. Build a fire first..."* This is the only place where cold mechanically blocks an action.
  - **`sauna_used` as a one-shot warmth beat.** Lighting the sauna stove sets the flag and runs the authored "the place belongs to the part of you that loved it" prose. There is no recurring warmth value; it is a single Act I beat.
  - **Cabin dark/cold description.** When the cabin has neither fire nor mains power, its description ends *"The cabin is dark. Cold seeps through the floorboards."* (`map.py`). This is descriptive, not damaging.
  - **The Lyer's chill as authored prose.** The Act II approach uses *"The temperature drops, not gradually, a wall of cold against your face. The silence becomes absolute."* The cold around the Lyer is a fixed beat, not a heat-map.
- **Aspirational (not yet implemented):**
  - A temperature or exposure value on `Player` / `WorldState`. There is no `cold`, `warmth`, `temperature`, or `exposure` field.
  - Damage from being outdoors too long, wet clothes, falling in the lake, snowstorms. None of these consequences exist in code.
  - Warm clothing items, hot drinks as warmth-restorers, a thermos. The flavour text in the Inventory section above ("thermos of hot coffee") is aspirational.
  - Cold-driven action failure (slowed actions, fumbled inputs). Currently only **Fear** modulates action reliability.
- **Creeping dread tie-in (aspirational shape):**
  - If a temperature stat were added, the Lyer's approach should drive it down regardless of nearby fire. The authored *"wall of cold"* already implies this; the mechanic would make it numeric.
  - Some rooms ("unnaturally cold even with fire nearby") would need a per-room ambient temperature override. Today, room descriptions handle this in prose alone — see the wrong-layer cabin in `map.py`.

---

## 🔚 Death & Failure

- **Possible Fail States:**
  - Physical death (injury, exposure, fall).
  - Psychological collapse (max fear).
  - Encountering the Lyer unprepared.
- **Game Over Flavor:**
  - No “you died” screens — just slow, inevitable loss of control.
  - Final moments may be dreamlike or narrated from the Lyer’s POV.

---

## 🛌 Sleep & Dreams

**Status:** Partially implemented — `first_morning` is a real one-shot state flag with an authored beat. Recurring sleep, dream content, and dream-driven fear are aspirational.

- **What's implemented today:**
  - **`first_morning: bool` on `WorldState`.** Default `False`. Set to `True` exactly once, by `use bed` in `actions/use.py`, when its preconditions are met.
  - **Preconditions to sleep.** The bed path checks three gates in order:
    1. `fire_lit` — narrated as *"The bed is cold. The cabin is colder. Build a fire first..."*
    2. `voicemail_heard` and `footage_reviewed` — narrated as *"There's something you haven't done yet. The phone. The feeds."*
    3. If both pass: sleep fires.
  - **The authored sleep beat.** The full passage is in `actions/use.py` (the bed branch). It ends *"Sleep comes. Then, later, the silence of the first morning."* This is canonical authored prose — not AI flavour.
  - **Downstream effect.** `first_morning == True` is the precondition for the Act II climax: in `map.py`, any attempt to leave `old_woods` after `first_morning` with `wrongness.threshold_met()` and the player still in the real layer triggers the Lyer beat rather than the move. See `docs/game_mechanics/wrongness-mechanic.md`.
  - **No re-sleep.** Re-using the bed once `first_morning` is set returns *"Not now. The morning is waiting outside, and so is something else."* There is no Act II / Act III / Act IV sleep loop.
- **Aspirational (not yet implemented):**
  - **Repeatable sleep** as a fear/health restorer. Today `first_morning` is a one-shot gate, not a recurring rest mechanic.
  - **Dream content as authored beats.** The current bed prose alludes to memory (*"the scraping sound from when you were small"*) but does not branch by world state. A dream system would let dreams change as wrongness, recognition, or the world layer change — and could surface tells or memory fragments inside the dream.
  - **Fear spikes from sleep.** The fiction supports nightmares; the mechanic does not exist.
  - **Sleep refused / sleep impossible** at high wrongness or after recognition. Currently `first_morning` is set once and the bed is closed.
- **Cross-reference:** `world_state.py` (`first_morning` field), `actions/use.py` (the bed branch), `map.py` (the `first_morning + threshold_met()` Lyer-encounter gate).

---

## 🎯 Future Mechanics To Consider

- Hunger/thirst (limited, avoid micro-management)
- Sound (stealth vs noise-based threat detection)
- Rituals or symbols (non-combat interactions with minions)
- Recurring sleep and dream content (see **Sleep & Dreams** above — the `first_morning` one-shot would need to become a loop, with dream prose branching on wrongness / recognition / layer)
- Real-time elements? (e.g. forced decisions under a ticking clock)

---

## Memory Fragments

Certain locations trigger **non-interactive narrative fragments**—short written scenes that appear on screen as *memories*, *echoes*, or *emotional flashbacks*. These are not voiced or animated, just pure text, lightly styled, fading in and out. They are intended to quietly deepen the story, develop character relationships, and build atmosphere without explicit exposition.

Fragments may appear:
- When entering key locations (e.g. sauna porch, lake path, main cabin steps)
- After specific events (e.g. lighting the stove, opening a box, finishing a fear event)
- Based on time of day or weather (optional)

They do **not** interrupt gameplay. They require no player input. They appear for ~10 seconds, then fade. Think of them as *the cabin itself remembering something*, or *John reliving a moment under stress*. In some cases, they may represent **the Lyer surfacing memory as a form of influence**.

These fragments are never introduced. No “Cutscene” or “Flashback.” They simply *happen*, quietly and without explanation.

---

### Example: The Dare

> *He crouched by the sauna steps, snow biting through his boots. She was already out there—naked, barefoot, the bucket above her head like a statue.*  
> *He braced to take the photo, then hesitated.*  
> *The trees were quiet. Too quiet.*  
> *He turned, scanning the mist. Nothing moved.*  
> *“John?” she called, cheerful and distant.*  
> *He looked back. “Yeah—go for it.”*  
> *Later, he wouldn’t remember the photo. Only the pause. And the way the woods felt… wrong.*

Triggered when player approaches the sauna building **for the first time**, regardless of time of day or purpose.

---

### Implementation Notes

- Fragments should be rare. No more than 10–15 total across the game.
- Can be replayed via journal or memory menu if included.
- Each one deepens the player’s understanding of **John**, **Nika**, or the Lyer.
- Fragments should avoid obvious horror tropes. Focus on tone, tension, atmosphere.
- Keep them under 100 words unless critical.