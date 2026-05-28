# Effects Pipeline

## Overview

An **effect** is the small, structured side of an action's outcome — a fear
delta, a health delta, an inventory add or remove — applied to player state
after the action has been interpreted and its narration prepared. Effects
are deliberately separated from narration: `ActionResult.feedback` carries
the prose, and the model's `Intent.effects` payload carries the numbers.
The render layer reads the feedback; the engine reads the effects. The two
never share a code path.

This separation exists for two reasons. First, narration is authored or
AI-flavoured, while state changes must be bounded and predictable.
Second, the model is allowed to propose effects in free-text replies, and
the engine has to filter those proposals before applying anything — the
model proposes, the engine disposes. The pipeline documented here is that
boundary.

There are two structurally distinct payloads on a turn:

- **`Intent.effects`** — proposed by the AI interpreter (or by rule-based
  fallback). Sanitised before it leaves `ai_interpreter.interpret()`.
  Applied to `Player` and inventory by the engine.
- **`ActionResult.state_changes`** — set by an action's `execute()` method.
  Consumed by the engine's event handler (`_handle_action_events`) to
  parameterise events like `fire_lit`, `wildlife_attack`, or
  `ending_refused`. World-state flag changes (e.g. `fire_lit = True`) are
  mutated directly inside `Action.execute()`, not applied from
  `state_changes` reflectively.

These two channels overlap on the surface — both can mention fear/health
deltas in their dict — but they are read by different code and serve
different purposes. The overlap is described in detail below.

## The two payloads

### `Intent.effects`

Defined on `Intent` in `game/ai_interpreter.py`:

```python
effects: Optional[Dict[str, Any]] = None
# {fear:int, health:int, inventory_add:[], inventory_remove:[]}
```

This is what the model is allowed to ask for. The schema is fixed; nothing
else in this dict is read by the engine.

### `ActionResult.state_changes`

Defined on `ActionResult` in `game/actions/base.py`:

```python
state_changes: Dict[str, Any] = field(default_factory=dict)
```

This is a free-form payload set by actions. Its keys are conventional, not
enforced — `item_name`, `from_room_id`, `to_room_id`, `direction`,
`fire_lit`, `voicemail_heard`, `fear_reduction`, `health_damage`,
`fear_increase`, `world_layer`, `ending`, `anomaly`, and so on. The keys
are consumed by `GameEngine._handle_action_events()` per event type. See
that method for the exhaustive list of recognised keys.

`state_changes` is **not** read by the effect-application path. An action
that wants to change the player's fear or health does so by either (a)
mutating `ctx.player` inside `execute()` directly, or (b) emitting an event
like `wildlife_attack` and shipping the numeric in `state_changes` for the
engine's event handler to apply (`game_engine.py` around the
`wildlife_attack` and `thrown_into_darkness` branches).

## Effect kinds

The four kinds the engine actually applies from `Intent.effects`:

| Kind | Field | Range | Clamping |
|------|-------|-------|----------|
| Fear delta | `fear` | int in `[-2, +2]` | Clamped at interpreter and again at engine. Player fear is then clamped to `[0, 100]`. |
| Health delta | `health` | int in `[-2, +2]` | Same — clamped at interpreter and engine. Player health clamped to `[0, 100]`. |
| Inventory add | `inventory_add` | list of item-name strings | Each name must already be in `room_items` or `inventory` at interpret time. At apply time, the item must exist in the game's item registry **and** still be in the current room. |
| Inventory remove | `inventory_remove` | list of item-name strings | Each name must already be in `inventory` at interpret time. At apply time, removal is silently no-op if the player no longer holds it. |

The bounds are deliberately narrow. The model can nudge — not push. A
single turn cannot cost more than two points of either stat through
`Intent.effects`. Large state changes (the Act II climax bleeding +40
fear / -20 health, wildlife attacks, fire's comfort delta) come from
`Action.execute()` or `_handle_action_events()`, not from the
interpreter's payload.

Anything else the model puts in `effects` — additional keys, extra fields,
nested objects — is dropped on the floor by the sanitiser. The sanitiser
constructs a fresh dict with exactly the four keys above.

## Order of application

Per turn, in `GameEngine.handle_user_input()`:

1. `InputHandler.parse()` — system commands (`quit`, `save`, `load`,
   quest screen, map screen) are handled and the turn ends. None of those
   paths apply effects.
2. `interpret()` (in `ai_interpreter.py`) — returns an `Intent` carrying
   a **sanitised** `effects` dict. The sanitisation happens inside
   `interpret()` before the function returns (see "AI sanitisation"
   below).
3. `ActionRegistry.execute()` — produces an `ActionResult` (or `None`
   for an unknown action). World-state flags the action wants to set
   (e.g. `fire_lit = True`) are mutated inside `execute()` itself.
4. **`_apply_effects(intent, skip_inventory=...)`** — the effect-
   application step. Reads `intent.effects` and mutates `self.player`
   and inventory.
5. `_last_feedback = result.feedback` — narration is queued for the
   next render.
6. `_handle_action_events(result, intent)` — turns
   `result.events` into `EventBus` emissions, parameterised by
   `result.state_changes`. This is also where some "large" state
   changes are applied (e.g. wildlife attack damage, throw-into-
   darkness fear).
7. `_check_death()` — fear/health thresholds checked. Death narration,
   if any, lands after the action's own feedback.

The two flows differ in exactly two cases:

- If `ActionRegistry.execute()` returns `None` (action name not
  recognised), effects are still applied — but with `skip_inventory=True`.
  The fear/health deltas land; the inventory adds/removes do not. This
  prevents the model from rearranging the inventory on an action the
  engine refused to run.
- If `result.success` is `False`, effects are applied with
  `skip_inventory=True` for the same reason — a failed action should not
  let the model pickpocket the room. Fear/health deltas still apply, so
  failure can still feel.

## AI sanitisation

The boundary that matters lives in `ai_interpreter.py:interpret()`,
roughly lines 638–655. After the model returns JSON, the interpreter:

1. Reads `data.get("effects") or {}`. Non-dict values are coerced to `{}`.
2. Reads `fear` and `health` as `int`, clamps each to `[-2, +2]`.
3. Reads `inventory_add` and filters it: an entry survives only if it
   is a string and matches a name in `set(room_items) | set(inventory)`
   from the AI context. The model cannot add an item the engine hasn't
   told it about.
4. Reads `inventory_remove` and filters it: an entry survives only if
   it matches a name in `set(inventory)`. The model cannot remove an
   item the player isn't holding.
5. Constructs `sanitized_effects` as a fresh dict with exactly four
   keys (`fear`, `health`, `inventory_add`, `inventory_remove`) and
   attaches it to the returned `Intent`.

The engine then clamps again at apply time (`_apply_effects` clamps
fear/health to `[-2, +2]` a second time, and the player's stats are
clamped to `[0, 100]` after the delta). The double clamp is intentional:
`Intent` is a public-ish dataclass that can be constructed by callers
other than `interpret()` (rule-based fallbacks, tests, dev tooling), and
the engine treats the sanitiser as an outer wall, not the only wall.

What sanitisation does **not** do:

- It does not validate the `action` against game state (that happens
  elsewhere — e.g. movement direction is rewritten to `none` if the
  exit isn't real, and `_act_v_offer_active()` gates the offer prompt).
- It does not authenticate item names against the global item registry.
  It checks only what the AI context said was visible. Apply-time then
  checks the registry and the current room.
- It does not strip `inventory_add` items that the model already says
  the player holds. If the model proposes adding an item already in
  inventory, the apply step's `room.has_item(item_name)` check will
  fail (because the item is in inventory, not the room), and the add
  is silently dropped.

## Authoring guidance

### Use `world_state` mutations for authored beats

If a story-critical flag flips (`fire_lit`, `voicemail_heard`,
`footage_reviewed`, `sauna_used`, `first_morning`, `recognition`,
`world_layer`, `ending`), set it directly on `ctx.world_state` inside the
action's `execute()` and ship the narration in `feedback`. Do **not**
expect the engine to apply story flags from `state_changes`. Read
`actions/refuse.py` and `actions/light.py` as canonical examples:
`refuse.py` calls `ws.exit_wrong_layer()` and `ws.ending = "refused"`
inline, then ships `state_changes={"world_layer": "real", "ending":
"refused"}` purely as a mirror for the event handler — the world state
has already changed.

This pattern keeps state mutation co-located with the prose that earns
it, which is the same rule documented in
`docs/game_mechanics/world-layers-mechanic.md` and
`docs/game_mechanics/recognition-and-refusal.md`: no silent flag flips.

### Use `state_changes` for event parameterisation

When an action emits an event the engine needs to handle, ship the
event's parameters in `state_changes`. The keys read by the engine
today, by event name:

| Event | Keys consumed from `state_changes` |
|-------|-------------------------------------|
| `player_moved` | `from_room_id`, `to_room_id`, `direction` |
| `item_taken` / `item_dropped` | `item_name` |
| `fuel_gathered` | `item_name` |
| `item_thrown` | `item_name`, `target` |
| `thrown_into_darkness` | `fear_increase` (default `5`) — applied directly to `player.fear` |
| `fire_lit` | `fear_reduction` (default `5`) — subtracted from `player.fear` |
| `fire_no_fuel`, `use_fireplace_no_fuel`, `use_fireplace`, `use_light_switch_no_power`, `lights_on`, `power_restored` | (none — these emit a flagged event with no payload) |
| `wildlife_provoked` | `target`, `provoke_result` |
| `wildlife_attack` | `health_damage`, `fear_increase` — applied directly to player |

The "applied directly" rows are the engine's escape hatch for state
changes larger than the interpreter's `[-2, +2]` window. They are
hand-wired per event in `_handle_action_events()` and are not part of
the generic effects pipeline.

### Use `Intent.effects` for AI-flavoured nudges only

Small, sensory consequences the AI invents around free-text input — a
flinch worth +1 fear, a stubbed shin worth -1 health — flow through
`Intent.effects`. The interpreter is the only thing that constructs these
in production. Hardcoded rule-based intents
(`_rule_based()` in `ai_interpreter.py`) always pass `effects=None`;
trivial commands like movement and inventory do not nudge stats by this
route.

If you need an action to apply a deterministic ±1 nudge, set it inside
`execute()` on `ctx.player` directly. Don't synthesise an `Intent.effects`
dict in the action layer.

### Don't extend the `effects` schema casually

Adding a fifth effect kind means three places change: the system-prompt
schema in `ai_interpreter.py` (`_SYSTEM_PROMPT_TEMPLATE`), the sanitiser
inside `interpret()`, and the apply site (`GameEngine._apply_effects`).
A new kind also widens the surface the model can affect — keep the
bounded-nudge ethos and ask whether the change really belongs in
`state_changes` or in direct `world_state` mutation instead.

## Code anchors

- `game/actions/base.py` — `ActionResult` shape, including the
  `state_changes` field and the `success_result` / `failure_result`
  factories.
- `game/ai_interpreter.py` — `Intent.effects` schema (around line 112),
  the system-prompt schema (`_SYSTEM_PROMPT_TEMPLATE`, defined at line 229
and formatted at line 289),
  and the sanitiser inside `interpret()` (effects block around lines
  638–655).
- `game/game_engine.py` — turn pipeline in `handle_user_input()`
  (around lines 123–169), `_apply_effects()` (around lines 255–286),
  `_handle_action_events()` (around lines 288–372).
- Related architecture docs:
  - `docs/architecture/architecture.md` — data-flow diagram showing
    where effects sit between action execution and event emission.
  - `docs/architecture/developer-guide.md` — broader contributor guide.
