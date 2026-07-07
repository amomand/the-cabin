# Quest: Warm Up

## Summary
Restore power and warmth to the cabin by flipping the main circuit breaker and lighting a fire.

## Trigger Conditions
This quest can be triggered by any of the following (see `create_warm_up_quest()` in `game/quests.py`):
- Entering the "lakeside" room.
- Attempting to light the fireplace.
- Attempting to turn on the lights, or using the light switch.
- Using the fireplace or the circuit breaker.

## Quest Start Text
The lights don't respond. The hearth is cold.  
No power. No warmth. The cabin breathes its chill into your hands.  

You won't last the night like this. The breaker first, then a fire. Your body has already decided, even as your mind catches up.

## Objective
Flip the main circuit breaker in the konttori, gather firewood (the woodshed is in the cabin grounds; note the in-game quest text currently says lakeside), and light the fire in the cabin. There is no visible checklist: progress surfaces only through the update lines below and the held-thought view.

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

## On Completion
- Display message:  
  _“The cabin hums with life again. Warmth creeps back into your limbs.”_

## Held-Thought Text (when active)
**Warm Up**  
The cold won't keep. Power first, then warmth.  
The breaker is in the konttori. There's wood down by the lakeside. The hearth is laid and waiting.

Your hands know the order of it.

## Held-Thought Text (no active quest)
When nothing is active, the held-thought view comes from `QuestManager.get_active_quest_display()`:
_“Nothing pulls at you just now. Only the cold, and the quiet, and the work your hands already know.”_

(`Quest.inactive_text` defaults to _“Nothing calls to you yet.”_ but no current command surfaces an individual inactive quest's text.)
