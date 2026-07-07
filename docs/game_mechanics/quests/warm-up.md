# Quest: Warm Up

## Summary
Restore power and warmth to the cabin by flipping the main circuit breaker and lighting a fire.

## Trigger Conditions
This quest can be triggered by any attempt to restore heat or power:
- Lighting or using the fireplace.
- Turning on the lights, using the light switch, or flipping the circuit breaker.

Under the hood these are two trigger actions: fireplace attempts arm the quest
via `light_fire`/`use_fireplace`, and every power or light attempt (lights,
switch, breaker) arms it via the single `turn_on_lights` action.

## Quest Start Text
The lights don’t respond. The hearth is cold.  
No power. No warmth. The cabin breathes its chill into your hands.  

You won’t last the night like this. The breaker first, then a fire. Your body has already decided, even as your mind catches up.

## Steps
- [ ] Flip the main circuit breaker (in the konttori)
- [ ] Gather firewood (from the woodshed in the cabin grounds)
- [ ] Light the fire (in the cabin)

## Quest Update Events
- **If player tries to light fire with no firewood:**  
  _“You have no fuel.”_

- **When fire is successfully lit:**  
  _“The fire crackles softly, shadows dancing against the log walls. It’s warm now.”_

## Completion Condition
This quest is completed automatically when both of the following conditions are met:
- The circuit breaker has been flipped.
- The fire has been lit.

## On Completion
- The quest is recorded in the quest manager's completed quests.
- Display message:  
  _“The cabin hums with life again. Warmth creeps back into your limbs.”_

## Quest Screen Text (when active)
**Warm Up**  
The cold won’t keep. Power first, then warmth.  
The breaker is in the konttori. There’s wood in the woodshed outside. The hearth is laid and waiting.

Your hands know the order of it.

## Quest Screen Text (when inactive)
_“Nothing calls to you yet.”_