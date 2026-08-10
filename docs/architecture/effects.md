# Effects Pipeline

## Overview

The turn core handles two deliberately separate effect channels:

- `Intent.effects` contains model-proposed fear, health, and inventory nudges.
  The interpreter sanitises it and `turn.apply_effects()` applies it only when
  the action result permits model effects.
- `ActionResult.requests` contains ordered, typed requests from an action to
  the shared turn coordinator. Requests carry every field their handler needs;
  there is no free-form payload dictionary or fallback value lookup.

`ActionResult.model_effects` is the policy between authored action truth and
model suggestions. Ordinary results use `ModelEffectsPolicy.APPLY`.
`ActionResult.authored(...)` uses `BLOCK`, so the authored narration, direct
state mutation, and typed requests are the complete outcome of that turn.

## Model-proposed effects

`Intent.effects` has four recognised fields:

| Kind | Field | Boundary |
|------|-------|----------|
| Fear delta | `fear` | Integer clamped to `[-2, +2]`; resulting fear clamped to `[0, 100]`. |
| Health delta | `health` | Integer clamped to `[-2, +2]`; resulting health clamped to `[0, 100]`. |
| Inventory add | `inventory_add` | Item must be visible to the interpreter, registered by the map, carryable, and still in the current room. |
| Inventory remove | `inventory_remove` | Item must already be in inventory; a missing item is a no-op. |

The interpreter constructs a fresh sanitised dictionary containing only those
fields. The shared turn core clamps again at application time because callers
other than the interpreter can construct an `Intent`.

Failed or unknown actions apply only fear and health nudges. Inventory changes
are skipped so a fall-through cannot pick up or remove an item. Authored
results skip all model-proposed effects without mutating the input `Intent`.

## Authored state and turn requests

Story state stays beside the narration that earns it. An action sets fields
such as `fire_lit`, `voicemail_heard`, `world_layer`, `ending`, or
`reunion_stage` directly on `ctx.world_state` and returns the beat with
`ActionResult.authored(...)`.

Cross-cutting effects use the constrained request union in
`game/events/requests.py`. Each frozen dataclass represents one real contract,
for example:

```python
return ActionResult.authored(
    feedback="The kindling catches. Heat begins at the hearth and nowhere else.",
    requests=[FireLitRequest(fear_reduction=5)],
)
```

Required payload fields have no defaults. Omitting `fear_reduction`, a movement
endpoint, or an item identity fails when the request is constructed.
`ActionResult` also rejects objects outside the union at runtime, including the
old arbitrary string labels.

Requests currently cover:

| Request | Shared handling |
|---------|-----------------|
| `PlayerMovedRequest` | Emits `PlayerMovedEvent`. |
| `ItemTakenRequest`, `ItemDroppedRequest`, `ItemThrownRequest` | Emit the corresponding item event. |
| `FuelGatheredRequest` | Emits `FuelGatheredEvent`. |
| `PowerRestoredRequest` | Emits `PowerRestoredEvent`. |
| `FireLitRequest` | Emits `FireLitEvent`, then applies the declared fear reduction. |
| `FireAttemptRequest` | Emits `FireAttemptEvent` with both inventory facts. |
| `LightSwitchUsedRequest`, `FireplaceUsedRequest` | Emit their flagged events. |
| `DarknessFearRequest` | Applies the declared fear increase without a bus event. |

The request tuple is ordered. `turn.handle_action_events()` processes each
request completely before advancing to the next, preserving EventBus ordering
and state-change ordering across terminal and web play.

## Turn order

For a game action, `turn.take_turn()`:

1. Builds AI context and interprets the input.
2. Executes the registered action.
3. Applies permitted `Intent.effects`.
4. Sets `ActionResult.feedback` on the surface.
5. Dispatches `ActionResult.requests` through `handle_action_events()`.

Quest and cutscene listeners run synchronously during step 5 and may replace
the action feedback. The surface checks death and endings after the shared turn
core returns.

## Authoring guidance

- Put story-critical mutations directly in the action that owns their prose.
- Use `ActionResult.authored(...)` when model effects must not decorate or
  contradict a deterministic beat.
- Add a small request dataclass when EventBus publication or a shared stat
  change is genuinely required. Make every consumed payload field explicit.
- Do not create labels for observation, replay, or ending branches that have no
  runtime consumer. Tests should characterise the narration and state gate.
- Keep model-proposed effects to bounded, sensory nudges. Expanding the schema
  changes the prompt, sanitiser, and application trust boundary.

## Code anchors

- `game/actions/base.py` — `ActionResult`, `ModelEffectsPolicy`, and factories.
- `game/events/requests.py` — the typed action-to-turn request union.
- `game/turn.py` — model-effect application and typed request dispatch.
- `game/events/types.py` — public EventBus payloads.
- `game/ai_interpreter.py` — model effect schema and sanitisation.
