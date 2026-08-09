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
> The switch gives you nothing. The hearth is cold.
> Your breath shows in front of you. You rub your hands and turn back to the porch cupboard.

## Objective
Flip the main circuit breaker in the porch cupboard, gather firewood (the woodshed is in the cabin grounds), and light the fire in the cabin. There is no visible checklist: progress surfaces only through the update lines below and the held-thought view.

## Quest Update Events
- **If player tries to light fire with no firewood:**  
  _“The grate is bare. There is split wood in the shed.”_

- **When fire is successfully lit:**  
  _“The first log catches. Heat begins to loosen your fingers.”_

- **When the circuit breaker is used:**  
  _“The ceiling bulb gives a weak yellow tremor. Somewhere in the wall, the fridge shudders awake.”_

- **When firewood is taken:**  
  _“You take the driest split logs from the stack.”_

## Completion Condition
This quest is completed automatically when both of the following world-state flags are set:
- `has_power` (the circuit breaker has been flipped).
- `fire_lit` (the fire has been lit).

Completion is re-checked on both `FireLitEvent` and `PowerRestoredEvent`, so the order does not matter: whichever of the two beats lands second closes the quest. A fire lit before the breaker is flipped completes normally.

## On Completion
- The quest is recorded in the quest manager's completed quests.
- Display message:  
  _“Light and heat, and the cabin stops taking from you. Your fingers come back first, then your face. You fetch two buckets from the pump house and hang the bedding near the hearth. Your hands remember the order.
  When you go to hang the blue mug, the hook is empty. The cupboard above the sink holds plates, old glasses, and the coffee tin. No mug. You set a white enamel one from your supplies on the table.”_

  This line has to work for whichever half lands second, so it names both. The
  previous text (“The cabin hums with life again”) described electrical
  restoration and printed on the fire-lit beat.

## Held-Thought Text (when active)
Warm Up
-------
The breaker is in the porch cupboard. Split logs are stacked in the woodshed. The hearth is laid.

Breaker. Wood. Fire. Your hands remember the order.

## Held-Thought Text (no active quest)
When nothing is active, the held-thought view comes from `QuestManager.get_active_quest_display()`:
_“Nothing pulls at you just now. Only the cold, and the quiet, and the work your hands already know.”_

(`Quest.inactive_text` defaults to _“Nothing calls to you yet.”_ but no current command surfaces an individual inactive quest's text.)
