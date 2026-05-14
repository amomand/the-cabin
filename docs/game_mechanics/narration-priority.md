# Narration Priority — Authored vs AI

## Overview

The Cabin uses an OpenAI model in the middle of its input pipeline, but the
model is not allowed to write the story. It parses free-text into an `Intent`
and, off-script, may supply a sentence or two of texture. The **authored
prose** in the action handlers is canonical for every story-critical beat.

This document is the rule for that split. AI is for **intent parsing**.
Authored prose is for the **scenes that earn the game's weight**. The two
appear in the same `ActionResult` shape, but they sit in very different
places in the pipeline, and confusing them produces the project's named
anti-pattern: **dual narration drift**.

The rule exists because the story beats — voicemail, camera, sauna, bed,
reunion, tells, correction-turn, refusal — were written by a human and
designed to land in a specific order and rhythm. Letting the model
paraphrase them costs the game its voice, and worse, lets the model fill in
gaps that the fiction needs to leave open. The Lyer's surface is silence,
not improvisation.

## The pipeline

The data flow is the same in both modes; the difference is which field of
the `Intent` an `Action` actually consumes.

```
User input
   │
   ▼
InputHandler          (quit / save / load — system commands only)
   │
   ▼
ai_interpreter.interpret()
   │
   ├── _rule_based()  (movement, inventory, look, help — no model call)
   │      │
   │      ▼
   │   Intent(action, args, confidence=1.0, reply=None, …)
   │
   └── model call     (creative or ambiguous input)
          │
          ▼
       Intent(action, args, confidence, reply, effects)
   │
   ▼
ActionRegistry  ─►  Action.execute(ctx: ActionContext) ─► ActionResult
   │
   ▼
EffectManager → EventBus → RenderManager
```

The model only ever produces an `Intent`. It never writes the player-facing
text on its own — the `Action` decides what the player sees, by returning a
`feedback` string inside `ActionResult`.

## Two ways AI appears in an `ActionResult`

There are exactly two legitimate shapes for AI involvement in player-facing
text. Everything else is a bug.

### 1. Intent parsing only (story-critical beats)

The model produces an `Intent` so the engine knows the player meant *use
the phone* or *talk to Nika*. The matching `Action` handler then returns
the authored prose for that beat and **does not consult** `ctx.ai_reply`.

This is the rule for every story-critical beat. The authored prose lives
inline in the handler, branches on state, and is returned unconditionally
once the branch is reached. Compare the voicemail handler and the camera
handler in `actions/use.py`: both return their fixed authored prose in the
gated `success_result(...)` call. Neither one references `ctx.ai_reply`.

### 2. Fallback flavour (generic, off-script)

For ambient verbs and generic item-use, the handler returns
`ctx.ai_reply or "<short authored fallback>"`. The model's one-liner gives
the moment texture; the fallback exists so a missing API key, an empty
reply, or an off-route player turn still gets an in-world sentence.

This is the rule for circuit breaker, matches, light switch, fireplace —
the small mechanical interactions whose prose is not narratively
load-bearing.

| Mode | Where the prose comes from | Where in code | When it applies |
|------|----------------------------|---------------|-----------------|
| Intent parsing only | Hard-coded `feedback="..."` in the handler | Story-beat branches (e.g. `phone`, `camera feed`, `sauna stove`, `bed`, `window`, `mug`, `nika`) | All story-critical beats |
| Fallback flavour | `ctx.ai_reply or "<authored fallback>"` | Generic item-use branches (e.g. `circuit breaker`, `matches`, `light switch`, `fireplace`) | Off-script, mechanical, ambient |

## The story-critical beat list

Per `CLAUDE.md`, these are the beats that must use the **intent parsing
only** mode. Each one is tied to a `WorldState` gate flag and to a fixed
piece of authored prose.

| Beat | Act | Gate flag(s) | Handler |
|------|-----|--------------|---------|
| Voicemail | I | `voicemail_heard` | `actions/use.py` — `item_lower == "phone"` |
| Camera feed | I | `footage_reviewed` | `actions/use.py` — `item_lower == "camera feed"` |
| Sauna | I | `sauna_used` | `actions/use.py` — `item_lower == "sauna stove"` |
| Bed (first morning) | I | `first_morning` (gated on `fire_lit`, `voicemail_heard`, `footage_reviewed`) | `actions/use.py` — `item_lower == "bed"` |
| Reunion: arrival → seated | III | `reunion_stage = "seated"` | `actions/use.py` — `item_lower == "nika"` |
| Reunion: seated → complete | III | `reunion_stage = "complete"` | `actions/use.py` — `item_lower == "mug"` |
| Act III tells (frost / knuckles / smile) | III | `wrongness.has(AnomalyID.X.value)` after `reunion_complete()` | `actions/use.py` — `window`, `mug`, `nika` post-`complete` branches |
| Wrong Outside pivot | III | `wrong_outside_seen` | `map.py` — `_wrong_outside_beat` |
| Correction-turn / recognition | IV | `recognition` | `map.py` — `_correction_turn_beat` |
| Refuse | V | `ending = "refused"` | `actions/refuse.py` |
| Accept | V | `ending = "accepted"` | `actions/accept.py` |

(The act labels above match the comments in `world_state.py`, `map.py`,
`anomalies.py`, the `refuse.py` / `accept.py` headers, and the dev seed
`seed_act4_recognition`. Match this labelling when adding new beats.)

What these beats share:

- They appear in `WorldState` as gate flags or stage literals.
- They have **fixed authored prose** written into the handler that fires
  them.
- They are the moments the player will quote back at you when describing
  the game. The model must not paraphrase them.

## The anti-pattern: dual narration drift

This pattern is wrong in a story-critical handler:

```python
# DON'T do this for a story beat.
return ActionResult.success_result(
    feedback=ctx.ai_reply or "Nika's voice. Terse, strained, not hers...",
    events=["voicemail_heard"],
)
```

The `or` looks defensive — "use the model if it gave us something, otherwise
fall back" — but for a story beat it inverts the priority. The model's reply
is almost always non-empty, so the authored prose only ever fires when the
API is down or the cache is cold. The canonical voicemail line becomes the
fallback, and the model gets to write the scene the rest of the time.

That is **dual narration drift** — the same beat narrated two different
ways depending on a model's mood. It is called out in `CLAUDE.md` under
"Anti-patterns specific to this codebase." Do not reintroduce it.

The correct shape for a story beat is unconditional:

```python
return ActionResult.success_result(
    feedback=(
        "You open the voicemail. Nika's voice. Terse, strained, not hers.\n"
        # ... rest of authored prose ...
    ),
    events=["voicemail_heard"],
    state_changes={"item_name": item.name, "voicemail_heard": True},
)
```

The handler does not read `ctx.ai_reply` at all on the story-beat branch.
The model parsed *use the phone* — its job is done.

## Where the rule does **not** apply

The intent-parsing-only rule is for story-critical beats. Off-script
interaction can and should use AI flavour. This is the texture layer:

- **Generic item-use.** Using a non-story item, or using a story item in a
  state where it has no scripted beat. The `ctx.ai_reply or "<fallback>"`
  pattern is fine here — see the circuit breaker, matches, light switch,
  and fireplace branches in `actions/use.py`.
- **Ambient verbs.** Throwing a stone, kicking a door, climbing on the
  furniture. The model is welcome to narrate it diegetically; the action's
  fallback ensures something in-world still lands if the model is silent.
- **Exploration prose where no room has authored a specific response.** If
  the room's `description_fn` or `wrong_description_fn` does not surface
  authored prose for a particular look or action, the model may carry the
  moment. The general `Use` fallback at the bottom of the handler —
  `ctx.ai_reply or f"You use the {item.name}."` — exists precisely for
  this.

The rule is positional, not blanket. Off-script flavour is a feature; it is
the texture that makes the world feel responsive between the authored
beats. Just keep it on the off-script side of the line.

## Authoring guidance

### Writing a new story-critical handler

Follow the canonical pattern in `actions/use.py` — the `window`, `mug`, and
`nika` handlers are the model:

1. **Branch by state.** The handler reads the relevant `WorldState` flag
   (`reunion_stage`, `world_layer`, an Act I bool) and dispatches to a
   stage-appropriate branch. Every reachable state has its own branch.
2. **Return authored prose in every branch.** Each branch's
   `success_result(...)` carries fixed `feedback="..."` text. Do not
   reference `ctx.ai_reply`. Do not fall back to the model.
3. **Mutate state inline.** If the beat advances a gate flag, do it in the
   same code path as the prose, not in an `on_enter` or ambient handler.
   This is the "silent flag flips for narrative beats" anti-pattern in
   `CLAUDE.md` — flags that change must be narrated in the same beat.
4. **Emit events.** Use `events=[...]` for anything downstream listeners
   need (quest progression, cutscenes, telemetry). Authored prose is the
   surface; events are the signal.
5. **Add a dev seed.** If the beat is reachable through a sequence of
   prior beats, add a seed in `game/devtools/seed_saves.py` so it can be
   played from a known state.

### Adjusting an existing story beat

Change the authored string in the handler. There is only one place. Do not
introduce a model-driven path "for variety." The single source of truth
keeps the prose under version control and reviewable.

### When in doubt

If a beat is on the story-critical list above, or feels like it would be —
it ends a scene, it changes Elli's relationship to the cabin or to Nika,
the player will remember it — assume it is. Write authored prose. Do not
reach for `ctx.ai_reply`.

## Diegetic constraints

- The split is invisible to the player. There is no surface that says
  "scripted" vs "AI". The fiction reads as one voice because the authored
  beats hold the spine and the fallback flavour is short, sensory, and in
  the same register.
- AI flavour that breaks the fourth wall (mentions the model, says
  "invalid command", explains a check) is a bug regardless of which mode it
  appears in. See `docs/game_mechanics/diegetic_action_interpretor.md` for
  the prompt-side rules that keep model output in-world.
- Mechanics docs may name the Lyer plainly (per `CLAUDE.md`). Player-facing
  prose — authored or AI — must not.

## Code anchors

- `game/ai_interpreter.py` — `Intent` dataclass (`action`, `args`,
  `confidence`, `reply`, `effects`); `_rule_based()` for trivial commands;
  `interpret()` as the single entry point.
- `game/actions/base.py` — the `Action` ABC, `ActionContext` (the
  `ai_reply` property surfaces `intent.reply`), and `ActionResult` with
  `feedback`, `events`, `state_changes`.
- `game/actions/use.py` — the canonical reference. Story-critical branches
  (`phone`, `camera feed`, `sauna stove`, `bed`, `window`, `mug`, `nika`)
  return unconditional authored prose. Generic branches
  (`circuit breaker`, `matches`, `light switch`, `fireplace`, and the final
  `f"You use the {item.name}."` fallback) use `ctx.ai_reply or "..."`.
- `game/actions/refuse.py`, `game/actions/accept.py` — Act V endings;
  authored prose only, on every branch including the failure modes.
- `game/map.py` — `_wrong_outside_beat` and `_correction_turn_beat`;
  authored prose firing alongside the state mutation.
- `game/game_engine.py` — orchestration: `interpret()` → `Intent` →
  `ActionRegistry` → `Action.execute()` → `ActionResult`.
- Related mechanic docs:
  - `docs/game_mechanics/diegetic_action_interpretor.md` — the prompt-side
    rules that keep the model's output diegetic when fallback flavour does
    fire.
  - `docs/game_mechanics/reunion-mechanic.md` — the canonical example of a
    stage-branched story-beat handler in `actions/use.py`.
  - `docs/game_mechanics/recognition-and-refusal.md` — the Act III–V beats
    that depend on this rule.
