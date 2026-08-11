# Event Bus

## Overview

`EventBus` is a synchronous, in-process pub/sub channel. Actions do not emit
onto it directly. They return typed requests on `ActionResult.requests`; the
shared turn core translates those requests into the existing public
`GameEvent` dataclasses and emits them in request order.

That separation keeps actions independent of quest and cutscene listeners,
while keeping terminal and web dispatch identical.

## The bus

`game/events/bus.py` stores handlers by event class name:

| Member | Behaviour |
|--------|-----------|
| `subscribe(event_type: str, handler)` | Appends a handler for a class name such as `"FireLitEvent"`. |
| `unsubscribe(event_type: str, handler)` | Removes the first matching handler, or no-ops. |
| `emit(event: GameEvent)` | Calls subscribers for `type(event).__name__` synchronously in registration order. |
| `clear()` | Removes all handlers. |
| `handler_count` | Returns the total registered handlers. |

The EventBus string key is a documented public dispatch convention. It is
distinct from the removed action-side string protocol: listeners subscribe by
the class name of a typed event instance; actions return typed request objects.

## Requests and events

Request dataclasses live in `game/events/requests.py`. Bus event dataclasses
live in `game/events/types.py` and retain their existing class names and
payloads.

| Action request | EventBus output | Current subscribers |
|----------------|-----------------|---------------------|
| `PlayerMovedRequest` | `PlayerMovedEvent` | Quest, cutscene |
| `ItemTakenRequest` | `ItemTakenEvent` | None |
| `ItemDroppedRequest` | `ItemDroppedEvent` | None |
| `ItemThrownRequest` | `ItemThrownEvent` | None |
| `FuelGatheredRequest` | `FuelGatheredEvent` | Quest |
| `PowerRestoredRequest` | `PowerRestoredEvent` | Quest |
| `FireLitRequest` | `FireLitEvent` | Quest |
| `FireAttemptRequest` | `FireAttemptEvent` | Quest |
| `LightSwitchUsedRequest` | `LightSwitchUsedEvent` | Quest |
| `FireplaceUsedRequest` | `FireplaceUsedEvent` | Quest |

`DarknessFearRequest` is handled by the same ordered dispatcher but changes
fear directly and emits no bus event. `FireLitRequest` emits `FireLitEvent`
before applying its declared fear reduction, preserving the existing order.

The unused `QuestTriggeredEvent`, `QuestUpdatedEvent`, and
`QuestCompletedEvent` classes remain reserved. Quest listeners currently call
the quest manager and surface callbacks directly.

## Emission

An action names every required field when constructing a request:

```python
ctx.world_state["fire_lit"] = True
return ActionResult.authored(
    feedback="The kindling catches. Heat begins at the hearth and nowhere else.",
    requests=[FireLitRequest(fear_reduction=5)],
)
```

Requests are frozen dataclasses. Required payload fields have no defaults, and
`ActionResult` rejects values outside the constrained union. There is no
side-channel dictionary, silent fallback payload, or ignored label.

`turn.handle_action_events()` dispatches requests in tuple order. A request is
fully handled before the next begins, and each `event_bus.emit()` completes all
subscribers synchronously before returning.

## Turn and listener order

`turn.take_turn()` executes the action, applies any permitted model effects,
sets action feedback, then dispatches typed requests. Event listeners therefore
run before the surface renders and may replace the action's feedback through
the surface callbacks.

Both surfaces register the cutscene listener before the quest listener. That
ordering is deliberate: movement narration lands before a quest opening
triggered by the same move (#186). Do not reorder those listeners without a
new characterization test and explicit review.

## Adding an event

1. Add the public EventBus dataclass to `game/events/types.py` and export it if
   external imports need it.
2. Add a focused, payload-complete request dataclass to
   `game/events/requests.py` and include it in `TurnRequest` and
   `TURN_REQUEST_TYPES`.
3. Return the request from the action that owns the event.
4. Translate it once in `turn.handle_action_events()`. Do not add a
   surface-specific branch.
5. Subscribe a listener by the EventBus event class name where needed.
6. Test required payload construction, emitted event contents and order, and
   terminal/web parity.

If a branch has no EventBus or shared-state consumer, do not invent a marker
for it. Characterise its narration and direct state transition instead.

## Code anchors

- `game/events/bus.py` — synchronous bus implementation.
- `game/events/types.py` — public EventBus payloads.
- `game/events/requests.py` — typed action-to-turn protocol.
- `game/turn.py` — the one shared request dispatcher.
- `game/events/listeners/quest_listener.py` — quest subscriptions.
- `game/events/listeners/cutscene_listener.py` — movement/cutscene subscription.
- `game/game_engine.py` and `server/session.py` — surface-owned buses and thin
  shared-core wrappers.
