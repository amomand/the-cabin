# Item Mechanic

## Overview

Rooms can contain items. These items are described as part of the room’s environment, and can be picked up, examined, or used by the player. Items help drive interaction, puzzle-solving, survival, and narrative progression.

## Behaviour

- Each room may have **one or more items** available.
- Items may be visible in the room description or discovered through specific player actions like `look`, `search`, or `inspect`.
- Players can **pick up** items using commands like `take rope`, `pick up stone`, `grab matches`.
- Once picked up, the item is:
  1. **Removed from the room**
  2. **Added to the player’s inventory**
  3. **Confirmed back to the player with a message**, e.g.:
     - *“You pick up the stick. Stick added to inventory.”*
     - *“You take the rusted key. Key added to inventory.”*

- The player can **check their inventory** at any time using commands like `inventory`, `what am I carrying`, or `check items`.

- If an item is not in the room or is not `carryable`, the AI should respond with something like:
  - *“There’s no stick here to pick up.”*
  - *“That item can’t be picked up.”*

## Traits

Items may have one or more traits that influence how they behave:

- `carryable` — can be picked up and added to inventory
- `usable` — can be used in some way (e.g. key, tool)
- `throwable` — can be thrown as an action
- `weapon` — can be used to defend or attack
- `flammable` — can catch fire or be used to light things
- `edible` — can be consumed, possibly with side effects
- `cursed` — has a negative or supernatural effect

## Room Design

Each room can specify:

- The **maximum number of items** it can contain
- A **pool of possible item types** to draw from
- A **description template** that allows the AI to incorporate items into sensory outputs

## Interaction Examples

- `take rope`  
  → *“You pick up the coiled rope. Rope added to inventory.”*

- `inventory`  
  → *“You are carrying: a rope, a stone, and a matchbox.”*

- `use key on door`  
  → *“The key fits. With a reluctant click, the door unlocks.”*

---