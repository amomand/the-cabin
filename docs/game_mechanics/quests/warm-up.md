# Quest: Warm Up

## Summary
Restore power and warmth to the cabin by flipping the main circuit breaker and lighting a fire.

## Trigger Conditions
Walking into the cold cabin arms this quest (see `create_warm_up_quest()` in `game/quests.py`):
- Entering `cabin_main`.
- Attempting the fireplace with no fuel.

Under the hood the quest lists one location condition (`cabin_main`) and one action condition (`use_fireplace`). The location trigger carries activation, because entering is the only beat that precedes both halves of the objective.

`light_fire` and `turn_on_lights` are deliberately **not** trigger conditions. `QuestEventListener` runs `_check_triggers` on the success paths as well as the failure ones, so listing them meant flipping the breaker fired the opening overlay — text telling Elli the lights don't respond, printed at the exact moment she restored them. A beat that completes half the quest must never be the beat that opens it.

Ordering note: `GameEngine` and `WebGameSession` both register the cutscene listener before the quest listener, so the cabin entry cutscene lands ahead of this opening. Registered the other way round, the quest spoke about a room the player had not yet been told she had stepped into.

## Quest Start Text
The lights don't respond. The hearth is cold.  
No power. No warmth. The cabin breathes its chill into your hands.  

Your breath is going up in front of you, indoors. That is the whole of it, and you know what it means.

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

Completion is re-checked on both `FireLitEvent` and `PowerRestoredEvent`, so the order does not matter: whichever of the two beats lands second closes the quest. A fire lit before the breaker is flipped completes normally.

## On Completion
- The quest is recorded in the quest manager's completed quests.
- Display message:  
  _“Light and heat, and the cabin stops taking from you. Your fingers come back first, then your face. You had not noticed how held you were.”_

  This line has to work for whichever half lands second, so it names both. The
  previous text (“The cabin hums with life again”) described electrical
  restoration and printed on the fire-lit beat.

## Held-Thought Text (when active)
**Warm Up**  
The cold won't keep.  
The breaker is in the konttori. There's wood in the woodshed outside. The hearth is laid and waiting.

Your hands know the order of it.

## Held-Thought Text (no active quest)
When nothing is active, the held-thought view comes from `QuestManager.get_active_quest_display()`:
_“Nothing pulls at you just now. Only the cold, and the quiet, and the work your hands already know.”_

(`Quest.inactive_text` defaults to _“Nothing calls to you yet.”_ but no current command surfaces an individual inactive quest's text.)
