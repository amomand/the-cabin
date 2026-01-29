---
name: the-cabin-diegetic
description: Enforce diegetic immersion for The Cabin. All player-facing output stays in-world. Fourth-wall breaks are bugs.
---

# The Cabin: Diegetic Immersion

This skill governs all work that touches player-facing text in The Cabin.

## Core Principle

The game NEVER breaks the fourth wall. Every player input receives an in-character response. "You can't do that" does not exist.

## Rules

### Voice
- Second person, present tense
- Sensory and terse (1-3 sentences)
- Bleak, cold, atmospheric

### Input Handling
- Trivial commands (go north, inventory, look) may use rule-based parsing
- Creative, ambiguous, or impossible input MUST go to the AI
- Typos are silently corrected

### Impossible Actions
- Narrate a grounded failed attempt
- Apply consequences (fear, health, injury)
- Give soft in-world hints about what might work
- NEVER say "you can't do that" or "invalid command"

### Lore Protection
- The Lyer is implied, never explained
- It cannot be trivialized, killed easily, or joked about

### Blocked Actions
- Missing resources are described in-world: "Dry as bone—no fuel, no spark."
- Gate progression through fiction, not error messages

## Anti-Patterns (bugs if they appear)

- "Invalid command"
- "You can't do that here"
- "Error:", "Warning:", or any system language
- Third person narration
- Explaining game mechanics directly
- Generic fallback that doesn't respond to the specific input

## Examples

### Good Responses

**Player:** "I float into the air like a god"  
**Response:** "You brace, will your body upward—nothing. The ground holds you. Your knees ache from the effort."

**Player:** "light the stove"  
**Response:** "You rattle the stove's handle. Dry as bone—no fuel, no spark."

**Player:** "breathe deeply"  
**Response:** "You draw a slow breath. The cold air cuts your throat. It does not steady you."

**Player:** "punch the darkness"  
**Response:** "Your fist swings through empty air. Something shifts in the shadows. You freeze."

### Bad Responses (bugs)

- "You can't fly."
- "Invalid action: float"
- "There is no stove fuel in your inventory."
- "The darkness cannot be punched."
- "Try using a different command."

## Reference

See: `docs/game_mechanics/diegetic_action_interpretor.md`
