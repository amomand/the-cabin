# Quest: Warm Up

## Summary
Restore power and warmth to the cabin by flipping the main circuit breaker and lighting a fire.

## Trigger Conditions
This quest can be triggered by any of the following actions:
- Attempting to light the fireplace without power or fuel.
- Attempting to turn on the lights.
- Entering the "konttori" room.
- Entering the "cabin_grounds" room.

## Quest Start Text
The lights don’t respond. The hearth is cold.  
No power. No warmth. The cabin is freezing.  

**Find the fuse board and flip the circuit breaker. Then gather firewood and light the fire in the cabin.**

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
- Set global flag `power_and_heat_restored` = `True`
- Display message:  
  _“The cabin hums with life again. Warmth creeps back into your limbs.”_

## Quest Screen Text (when active)
**Warm Up**  
Restore power and warmth to the cabin.  
Flip the breaker in the konttori, gather firewood from the cabin grounds, and light the hearth.

## Quest Screen Text (when inactive)
_“Quests will appear here when active.”_