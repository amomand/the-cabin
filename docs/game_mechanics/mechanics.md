
# ⚙️ Game Mechanics – *The Cabin*

A survival horror text adventure grounded in realism and creeping dread.  
You are not a hero. You are just trying to make it through.

> This page is the original design sketch. Sections marked **Status** say
> what is implemented; the rest is aspiration, and some of it predates the
> rewritten canon. Where this page and `docs/lore/` disagree, the lore wins:
> the Lyer has no minions, there is no procedural map, and the story has no
> John. `docs/lore/playable-story.md` is the game-side reference for rooms,
> phases and object states; the per-mechanic pages in this directory describe
> what the code does.

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

- **Status:** Implemented as authored beats, not as a system. The one
  encounter is the Act II climax (`docs/game_mechanics/wrongness-mechanic.md`,
  `docs/game_mechanics/world-layers-mechanic.md`); it wounds and does not
  kill. The false cabin and the copy are `reunion-mechanic.md` and
  `recognition-and-refusal.md`.
- **What holds from the sketch:**
  - Presence brings cold and silence before anything is seen.
  - Its attention is the horror, and refusal, not courage, is the exit.
- **Retired:** early encounters as game over, "levelling up" courage, and
  lesser minions. The rewritten canon (`docs/lore/the_lyer.md`) has one
  creature, never seen clearly, and nothing that serves it.

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
  - **The hearth.** `LightAction` (and the `use matches` handler in `actions/use_handlers/utilities.py`) requires both `matches` and `firewood` to set `world_state.fire_lit = True`. Without firewood the match burns out; without matches the firewood sits dark. Fire is optional; sleeping without it costs 10 health once.
  - **Mains power.** `cabin_main` exposes a `light switch` and the circuit breaker in the porch cupboard, behind the snow shovel. Flipping the switch before the breaker has been used returns the authored "the cabin remains dark" feedback with `LightSwitchUsedRequest(has_power=False)`, which emits the public event. After `use circuit breaker` sets `world_state.has_power = True`, the cabin's room description says *"The ceiling bulb burns weak and yellow."*
  - **Lit / dark cabin description.** `_cabin_description` in `map.py` composes heat and mains power independently. The hearth is either cold enough to show Elli's breath or giving back a little heat; the ceiling bulb is either dark or weak and yellow. All four combinations append to the base room description without making electric light sound like warmth.
  - **Darkness as a fear trigger.** Throwing an item outdoors returns a `DarknessFearRequest` whatever the named target, which the shared turn core applies to fear. This is the only place "darkness" is currently a mechanic and not a description.
- **Sources of Light:**
  - Matches + firewood → hearth fire (real items, real flag).
  - Circuit breaker + light switch → mains lighting (real items, real flag).
  - Moonlight / lake light / sky — narrative only; no item.
- **Aspirational (not yet implemented):**
  - Flashlights, batteries, candles, lanterns. No item of these names exists in `game/item.py`.
  - Light source reliability — batteries dying, wind extinguishing a match outdoors, fire burning down. The `fire_lit` flag does not decay.
  - Darkness-gated events ("only triggers in full dark", "needed to avoid minions", revealing hidden text). Room visibility is uniform; descriptions vary, content does not.
- **Authoring note:** the Lyer is described as cold and as swallowing sound (*"The cold comes first"* and *"The quiet closes over your ears like water"* in the Act II cutscene). That is authored prose, not a light-radius system.

---

## 🧭 Exploration

- **Status:** The map is authored, not generated: thirteen rooms in three
  locations, built in `game/map.py` and described in
  `docs/game_mechanics/map-mechanic.md`. `docs/lore/playable-story.md` holds
  the target layout for the #264 re-authoring, where routes close and open
  by story phase rather than by item finds.
- **World Structure (original sketch):**
  - A grid or graph of locations (cabin, forest, lake).
  - Some areas only accessible after certain events.
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

**Status:** A cold night has a one-off health consequence; ongoing exposure remains aspirational. The word "cold" carries enormous narrative weight today, but no temperature value, exposure timer, or hypothermia path is implemented. `fire_lit`, `sauna_used` and `slept_cold` distinguish heating, the optional sauna visit and the first night.

- **What's implemented today:**
  - **Cold sleep.** With no cabin fire, sleep is allowed and costs 10 health once. `slept_cold` preserves that history after later heating.
  - **`sauna_used` as a one-shot warmth beat.** Lighting the sauna stove sets the flag and runs the authored "the place belongs to the part of you that loved it" prose. There is no recurring warmth value; it is a single Act I beat.
  - **Cabin dark/cold description.** Without fire, the cabin description says *"The hearth is cold. Your breath shows in the room."* Without mains power, it adds *"The ceiling bulb stays dark."* This is descriptive, not damaging.
  - **The Lyer's chill as authored prose.** The Act II approach brings a wall of cold across Elli's face and stops her breath from showing. The cold around the Lyer is a fixed beat, not a heat-map.
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
  - **`first_morning: bool` on `WorldState`.** Default `False`. Set to `True` exactly once, by `use bed` in `actions/use_handlers/act_one.py`, when its preconditions are met.
  - **Preconditions to sleep.** The voicemail and frames are required, in that order at the main-room window. Power, fire and sauna are optional.
  - **The authored sleep beat.** The full passage is in `actions/use_handlers/act_one.py` (the bed handler). Dinner, the wine bottle, the empty mug hook, the physical camera check planned for daylight, and the first morning all mirror the published story's sequence.
  - **Downstream effect.** `first_morning == True` is the precondition for the Act II climax: in `map.py`, any attempt to leave `old_woods` after `first_morning` with `wrongness.threshold_met()` and the player still in the real layer triggers the Lyer beat rather than the move. See `docs/game_mechanics/wrongness-mechanic.md`.
  - **No re-sleep.** Re-using the bed once `first_morning` is set returns *"You have slept enough. The morning waits outside."* There is no Act II / Act III / Act IV sleep loop.
- **Aspirational (not yet implemented):**
  - **Repeatable sleep** as a fear/health restorer. Today `first_morning` is a one-shot gate, not a recurring rest mechanic.
  - **Dream content as authored beats.** The current bed prose carries memory into sleep and distinguishes warm and cold nights. A dream system would let dreams change as wrongness, recognition, or the world layer change — and could surface tells or memory fragments inside the dream.
  - **Fear spikes from sleep.** The fiction supports nightmares; the mechanic does not exist.
  - **Sleep refused / sleep impossible** at high wrongness or after recognition. Currently `first_morning` is set once and the bed is closed.
- **Cross-reference:** `world_state.py` (`first_morning` field), `actions/use_handlers/act_one.py` (the bed handler), `map.py` (the `first_morning + threshold_met()` Lyer-encounter gate).

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

They do **not** interrupt gameplay. They require no player input. They appear for ~10 seconds, then fade. Think of them as *the cabin itself remembering something*, or *a memory surfacing under stress*. In some cases, they may represent **the Lyer surfacing memory as a form of influence**.

These fragments are never introduced. No “Cutscene” or “Flashback.” They simply *happen*, quietly and without explanation.

---

### Example: the entry memory

The one fragment in the game today is inside the cabin-entry cutscene
(`game/story/cutscenes/entering-cabin.txt`): the scraping at nine years old,
and her grandmother's "before the forest moved". It fires once, on first
entry, and is never introduced as a memory. Any new fragment should work the
same way and draw on the canon material in `docs/lore/`: the lake path and
the towel, the sauna bench and the birthday cake, the box cutter and the
scar, the photograph by the till.

---

### Implementation Notes

- Fragments should be rare. No more than 10–15 total across the game.
- Not replayable in the current implementation (see Journal / Memory above); any future revisit mechanism must stay diegetic, not a menu.
- Each one deepens the player's understanding of Elli, Nika, or the Lyer.
  There is no John; he was cut from canon (`docs/lore/characters.md`).
- Fragments should avoid obvious horror tropes. Focus on tone, tension, atmosphere.
- Keep them under 100 words unless critical.
