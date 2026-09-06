# Event bus

`EventBus` is synchronous and in-process. Actions return typed requests;
[the effects pipeline](effects.md) owns their ordered dispatch and translation
into public events. This keeps actions independent of quest and cutscene
listeners and keeps terminal and web decisions together.

## Listener contract

The bus dispatches on the event class name, such as `PlayerMovedEvent`, and
calls subscribers in registration order. This string subscription convention
is public; it does not permit free-form action request labels. `unsubscribe`
removes the first matching handler and otherwise does nothing. See
[game/events/bus.py](../../game/events/bus.py) for the small API.

Both surfaces register the cutscene listener before the quest listener. That
ordering makes movement narration land before a quest opening triggered by the
same move. Preserve it when changing registration or add behaviour evidence for
an intentional change. Listeners run before rendering; authored feedback
priority follows [effects](effects.md#turn-order).

Quest listeners call the quest manager and surface callbacks directly. The
reserved `QuestTriggeredEvent`, `QuestUpdatedEvent` and `QuestCompletedEvent`
classes are not a second live publication path.

## Adding an event

Define the public payload in [events/types.py](../../game/events/types.py) and a
payload-complete request in [events/requests.py](../../game/events/requests.py),
including it in the constrained request union. Return that request from the
action owning the event and translate it once in
[turn.handle_action_events](../../game/turn.py). Subscribe the consumer by event
class name. Do not add a surface-specific dispatcher or a marker with no consumer.

Verify the emitted contents, relevant ordering and surface parity. The existing
[quest listener](../../game/events/listeners/quest_listener.py) and
[cutscene listener](../../game/events/listeners/cutscene_listener.py) show the
runtime subscriptions; code owns the subscriber inventory.
