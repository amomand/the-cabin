
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

- **Key Mechanic:**
  - Darkness increases fear passively.
  - Some events only trigger in full dark (or only *don’t* trigger if you have light).
- **Sources of Light:**
  - Matches, flashlight, fire, moonlight.
  - Some unreliable — batteries die, wind extinguishes.
- **Use Cases:**
  - Can reveal hidden symbols or texts.
  - May be needed to avoid minions.

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

- **Mechanic:**
  - Tracks key discoveries, dreams, and player thoughts.
  - May become unreliable at high fear or after supernatural events.
  - Some entries appear mysteriously — not written by the player.
- **Usage:**
  - Clues for puzzles or safe paths.
  - Narrative flavour, dread-building, unreliable narration tool.

---

## 🧊 Cold

- **Mechanic:**
  - Environmental threat that drains health or slows actions.
- **Triggers:**
  - Being outdoors too long without proper gear.
  - Wet clothes, falling into lake, snowstorms.
- **Countermeasures:**
  - Fire, sauna, hot drinks, warm clothing (if found).
- **Creeping Dread Tie-in:**
  - Cold intensifies around the Lyer.
  - Some places unnaturally cold even with fire nearby.

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

## 🎯 Future Mechanics To Consider

- Hunger/thirst (limited, avoid micro-management)
- Sound (stealth vs noise-based threat detection)
- Rituals or symbols (non-combat interactions with minions)
- Sleep and dreams (for storytelling and fear reduction — or spikes)
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