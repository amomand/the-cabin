# Quest: Warm Up

## Summary
Restore power and warmth to the cabin by flipping the main circuit breaker and lighting a fire.

## Trigger Conditions
This quest can be triggered by any attempt to restore heat or power (see `create_warm_up_quest()` in `game/quests.py`):
- Lighting or using the fireplace.
- Turning on the lights, using the light switch, or flipping the circuit breaker.

Under the hood the quest lists three action trigger conditions — `light_fire`, `use_fireplace`, and `turn_on_lights`. Fireplace attempts arm it via `light_fire`/`use_fireplace`; any power or light attempt arms it via `turn_on_lights` (the light switch and circuit breaker each emit a `turn_on_lights` action rather than triggering directly). Entering a room no longer arms it.

## Quest Start Text
The lights don't respond. The hearth is cold.  
No power. No warmth. The cabin breathes its chill into your hands.  

You won't last the night like this. The breaker first, then a fire. Your body has already decided, even as your mind catches up.

## Objective
Flip the main circuit breaker in the konttori, gather firewood (the woodshed is in the cabin grounds), and light the fire in the cabin. There is no visible checklist: progress surfaces only through the update lines below and the held-thought view.

## Quest Update Events
- **If player tries to light fire with no firewood:**  
  _“You have no fuel.”_

- **When fire is successfully lit:**  
  _“The fire crackles softly, shadows dancing against the log walls. It's warm now.”_

- **When the circuit breaker is used:**  
  _“Power hums through the cabin. The lights should work now.”_

- **When firewood is taken:**  
  _“You now have firewood to burn.”_

## Completion Condition
This quest is completed automatically when both of the following world-state flags are set:
- `has_power` (the circuit breaker has been flipped).
- `fire_lit` (the fire has been lit).

The completion check currently runs only on `FireLitEvent`, so the fire must be lit after power is restored. A fire lit before power leaves the quest stuck even once `has_power` becomes true, because power restoration does not re-check completion. (Known gap, tracked separately; not introduced by this doc pass.)

## On Completion
- The quest is recorded in the quest manager's completed quests.
- Display message:  
  _“The cabin hums with life again. Warmth creeps back into your limbs.”_

## Held-Thought Text (when active)
**Warm Up**  
The cold won't keep. Power first, then warmth.  
The breaker is in the konttori. There's wood in the woodshed outside. The hearth is laid and waiting.

Your hands know the order of it.

## Held-Thought Text (no active quest)
When nothing is active, the held-thought view comes from `QuestManager.get_active_quest_display()`:
_“Nothing pulls at you just now. Only the cold, and the quiet, and the work your hands already know.”_

(`Quest.inactive_text` defaults to _“Nothing calls to you yet.”_ but no current command surfaces an individual inactive quest's text.)
