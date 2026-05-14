# Event Bus

## Overview

The `EventBus` is a synchronous, in-process pub/sub channel that decouples
Actions from the systems that react to them. Actions emit events as a list
of short string identifiers on `ActionResult.events`; the engine translates
those strings into typed `GameEvent` dataclasses and dispatches them through
the bus; listeners that subscribed at startup react.

The point is decoupling. `LightAction` does not know that lighting a fire
might advance a quest, and the `QuestEventListener` does not know that
`LightAction` exists. They communicate only through `FireLitEvent`. New
listeners can subscribe to existing events without touching the action that
emits them. New emitters can fire an existing event without touching the
listeners that react to it.

The bus is intentionally minimal: dictionary of handlers keyed by event
class name, synchronous emission in subscription order, no priorities, no
async, no event queue.

## The bus

`game/events/bus.py` defines a single class.

| Member | Behaviour |
|--------|-----------|
| `subscribe(event_type: str, handler)` | Appends `handler` to the list for the event class name. Multiple handlers per type are allowed. |
| `unsubscribe(event_type: str, handler)` | Removes the first matching handler. Silently no-ops if absent. |
| `emit(event: GameEvent)` | Looks up `type(event).__name__` and calls each subscribed handler synchronously, in subscription order, passing the event instance. |
| `clear()` | Drops all handlers. Used in tests. |
| `handler_count` | Total handlers across all event types. Used in tests. |

`event_type` is the **class name as a string** (e.g. `"PlayerMovedEvent"`),
not the class itself. Handlers receive the event instance, so they can read
its typed fields directly.

The bus is owned by `GameEngine` (`game/game_engine.py`, constructor at
line 42). It is created with a default instance or injected for tests, and
listeners are registered in `_setup_event_listeners()` immediately after
construction.

## Event types

All event types are dataclasses defined in `game/events/types.py` and
exported from `game/events/__init__.py`. The base class `GameEvent` is
empty and exists only so handlers can be typed against a common parent.

| Event | Payload | Emitted from `_handle_action_events` on string | Currently subscribed by |
|-------|---------|-----------------------------------------------|--------------------------|
| `PlayerMovedEvent` | `from_room_id: str`, `to_room_id: str`, `direction: str` | `"player_moved"` | `QuestEventListener`, `CutsceneEventListener` |
| `ItemTakenEvent` | `item_name: str`, `room_id: str` | `"item_taken"` | (none) |
| `ItemDroppedEvent` | `item_name: str`, `room_id: str` | `"item_dropped"` | (none) |
| `ItemThrownEvent` | `item_name: str`, `target: Optional[str]`, `into_darkness: bool` | `"item_thrown"` | (none) |
| `PowerRestoredEvent` | — | `"power_restored"` | `QuestEventListener` |
| `FireLitEvent` | — | `"fire_lit"` | `QuestEventListener` |
| `FireAttemptEvent` | `has_fuel: bool`, `has_matches: bool` | `"fire_no_fuel"` | `QuestEventListener` |
| `LightSwitchUsedEvent` | `has_power: bool` | `"use_light_switch_no_power"`, `"lights_on"` | `QuestEventListener` |
| `FireplaceUsedEvent` | `has_fuel: bool` | `"use_fireplace"`, `"use_fireplace_no_fuel"` | `QuestEventListener` |
| `WildlifeProvokedEvent` | `wildlife_name: str`, `action: str`, `health_damage: int`, `fear_increase: int` | `"wildlife_provoked"` | (none) |
| `FuelGatheredEvent` | `item_name: str` | `"fuel_gathered"` | `QuestEventListener` |
| `QuestTriggeredEvent` | `quest_id: str`, `trigger_type: str`, `trigger_data: Dict[str, Any]` | (not emitted) | (none) |
| `QuestUpdatedEvent` | `event_name: str`, `event_data: Dict[str, Any]` | (not emitted) | (none) |
| `QuestCompletedEvent` | `quest_id: str` | (not emitted) | (none) |

The three `Quest*Event` types are defined but currently unused: the
`QuestEventListener` calls the quest manager directly through callbacks
(`on_quest_triggered`, `on_quest_updated`, `on_quest_completed`) rather
than re-emitting through the bus. They exist as a reserved vocabulary for a
future refactor.

Several emitted events (`ItemTakenEvent`, `ItemDroppedEvent`,
`ItemThrownEvent`, `WildlifeProvokedEvent`) have no subscribers today. They
are emitted by the engine but no listener reacts. Adding a listener that
subscribes to them does not require touching any emission code.

## Emission

Actions do not touch the `EventBus` directly. They return an `ActionResult`
(`game/actions/base.py`) whose `events` field is a `List[str]`. The strings
are short identifiers, **not** event class names — they are the keys the
engine matches in `_handle_action_events` to decide which typed event to
construct.

Worked example, `LightAction.execute` (`game/actions/light.py:21–26`):

```python
ctx.world_state["fire_lit"] = True
return ActionResult.success_result(
    feedback=ctx.ai_reply or "The matches catch and the firewood ignites. Warmth spreads through the cabin.",
    events=["fire_lit", "fire_success"],
    state_changes={"fire_lit": True, "fear_reduction": 5}
)
```

Two strings are emitted. `"fire_lit"` is the canonical event the engine
knows how to translate into `FireLitEvent`. `"fire_success"` is **not**
translated — there is no matching branch in `_handle_action_events`. It is
inert until a branch is added. This is the pattern: actions can list any
identifier; the engine only translates the ones it has explicit branches
for.

`state_changes` carries auxiliary data the engine needs when constructing
the typed event (e.g. `from_room_id`, `to_room_id`, `direction` for
`PlayerMovedEvent`) or applies as a direct side-effect (e.g.
`fear_reduction` reduces fear when `"fire_lit"` is emitted; `health_damage`
applies when `"wildlife_attack"` is emitted).

## Dispatch

`GameEngine.handle_user_input` (`game/game_engine.py:123`) runs the
following sequence on each turn, after the input handler has classified
input as a game action:

1. Build AI context (`_build_ai_context`).
2. Parse intent via `interpret()`.
3. Execute the action via `ActionRegistry.execute()` → `ActionResult`.
4. Apply AI-suggested effects (`_apply_effects`). If the action failed,
   skip inventory changes to prevent softlocks.
5. Set `_last_feedback` to `result.feedback`.
6. Call `_handle_action_events(result, intent)`.
7. Check death (`_check_death`).

`_handle_action_events` (`game/game_engine.py:288`) iterates
`result.events`. For each string it either:

- Constructs the matching `GameEvent` dataclass from `state_changes` and
  calls `self.event_bus.emit(...)`. Subscribed handlers run synchronously
  before the loop advances to the next event string.
- Applies a direct state mutation without going through the bus (e.g.
  `"thrown_into_darkness"` increases fear directly;
  `"wildlife_attack"` applies health damage and fear directly).
- Falls through silently if no branch matches.

Order matters. Events are emitted in the order the action lists them.
Handlers are called in subscription order — the order
`_setup_event_listeners` registers them: quest listener first, cutscene
listener second.

Effects are applied **before** events. The bus runs **before** rendering:
the next render call after the turn picks up any feedback or quest screen
written by event handlers via the callback pathway.

## Subscribers

Listeners live in `game/events/listeners/` and follow a uniform shape:
they expose a `register(event_bus)` method that calls
`event_bus.subscribe(...)` for each event they care about, and one
`_on_<event>` handler per subscription.

| Listener | File | Subscribes to | Reacts by |
|----------|------|---------------|-----------|
| `QuestEventListener` | `quest_listener.py` | `PlayerMovedEvent`, `FuelGatheredEvent`, `PowerRestoredEvent`, `FireLitEvent`, `FireAttemptEvent`, `LightSwitchUsedEvent`, `FireplaceUsedEvent` | Calls `quest_manager.check_triggers`, `check_updates`, `check_completion`, then invokes the engine callbacks `on_quest_triggered` / `on_quest_updated` / `on_quest_completed` if anything fired. |
| `CutsceneEventListener` | `cutscene_listener.py` | `PlayerMovedEvent` | Calls `cutscene_manager.check_and_play_cutscenes(from_room_id, to_room_id, player, world_state)`. |

`game/events/listeners/__init__.py` is empty — listeners are not auto-loaded.
`GameEngine._setup_event_listeners` constructs each listener with the
managers and state accessors it needs, then calls `register(self.event_bus)`.
Both listeners take state accessors as callables (`get_player`,
`get_world_state`) so they always see live state even though they are
constructed once at startup.

There are no ending-specific listeners today. The Act V endings
(`actions/accept.py`, `actions/refuse.py`) handle their state transitions
inline within the action rather than through the bus.

## Adding a new event end-to-end

Worked walk-through using `FireLitEvent` as the template.

### 1. Define the event type

In `game/events/types.py`:

```python
@dataclass
class FireLitEvent(GameEvent):
    """Emitted when a fire is successfully lit."""
    pass
```

Export it from `game/events/__init__.py` (`from game.events.types import
FireLitEvent`, and add to `__all__`).

### 2. Emit a string identifier from an Action

`game/actions/light.py:24` returns `events=["fire_lit", "fire_success"]` on
success. Pick a short snake-case identifier. If the listener will need
contextual data, put it in `state_changes` alongside the event string.

### 3. Translate the string in `_handle_action_events`

`game/game_engine.py:338`:

```python
elif event_name == "fire_lit":
    self.event_bus.emit(FireLitEvent())
    # Fire provides comfort — reduce fear
    fear_reduction = state_changes.get("fear_reduction", 5)
    self.player.fear = max(0, self.player.fear - fear_reduction)
```

Import the event class at the top of `game_engine.py`. Side effects that
are not the listener's job (here: the fear reduction) live in the engine
branch, not in the listener.

### 4. Subscribe a listener

`game/events/listeners/quest_listener.py:63`:

```python
event_bus.subscribe("FireLitEvent", self._on_fire_lit)
```

```python
def _on_fire_lit(self, event: FireLitEvent) -> None:
    self._check_triggers("action", {"action": "light_fire"})
    self._check_updates("fire_success", {"action": "light_fire", "success": True})
    self._check_completion()
```

If a brand new listener is needed, mirror the shape of
`QuestEventListener` or `CutsceneEventListener`: constructor takes managers
and state accessors, `register(event_bus)` wires subscriptions,
`_on_<event>` handlers do the work. Construct and register it in
`GameEngine._setup_event_listeners`.

### 5. Test

Add a unit test that emits the event directly against an `EventBus` and
asserts the handler ran. The bus is trivially testable in isolation: build
one, subscribe a spy, emit, assert. Pre-existing patterns live under
`tests/`.

## Anti-patterns

- **Subscribing to a raw string identifier.** Listeners subscribe to event
  class names (`"FireLitEvent"`), not to the action-side strings
  (`"fire_lit"`). The string-to-class translation only happens inside
  `_handle_action_events`.
- **Emitting from an Action directly.** Actions return events as strings on
  `ActionResult`. They do not import `EventBus` and they do not call
  `emit`. Keep the bus as a single dispatch point.
- **Putting narrative side effects in a listener.** Listeners advance
  game-mechanical state (quest progression, cutscene checks). Authored
  narrative beats live in the action or the room callback that owns them.
  See the "silent flag flips for narrative beats" anti-pattern in
  `CLAUDE.md`.
- **Relying on cross-listener ordering.** Subscription order is registration
  order, but listeners should not depend on each other firing first. If
  ordering matters, fold the logic into one listener.

## Code anchors

- `game/events/bus.py` — `EventBus`, `subscribe`, `unsubscribe`, `emit`,
  `clear`, `handler_count`.
- `game/events/types.py` — `GameEvent` base and all fourteen concrete event
  dataclasses (lines 10–109).
- `game/events/__init__.py` — public exports.
- `game/events/listeners/quest_listener.py` — `QuestEventListener`,
  `register`, seven `_on_<event>` handlers.
- `game/events/listeners/cutscene_listener.py` — `CutsceneEventListener`,
  `register`, `_on_player_moved`.
- `game/actions/base.py:16–22` — `ActionResult.events: List[str]`,
  `state_changes: Dict[str, Any]`.
- `game/actions/light.py:21–26` — example emission (`"fire_lit"`).
- `game/game_engine.py:42–56` — bus construction and injection.
- `game/game_engine.py:66–85` — `_setup_event_listeners` wiring.
- `game/game_engine.py:166–167` — dispatch site inside the turn loop.
- `game/game_engine.py:288–372` — `_handle_action_events`, full
  string-to-event translation table.
