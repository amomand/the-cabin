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
reunion, tells, the consent door, the night seams, the knowing, the dawn
choice, the walk out, the coda — were written by a human and
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
ActionResult.model_effects policy ─┬─ APPLY ─► turn.apply_effects()
                                  └─ BLOCK (authored beat)
   │
   ▼
EventBus → per-surface render
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
once the branch is reached. Compare the voicemail handler in
`actions/use_handlers/phone.py` and the camera handler in
`actions/use_handlers/act_one.py`: both return their fixed authored prose in the
gated `ActionResult.authored(...)` call. Neither one references `ctx.ai_reply`.
That constructor also blocks model-proposed effects, leaving the authored
narration and deterministic state changes as the complete outcome of the beat.

### 2. Fallback flavour (generic, off-script)

For ambient verbs and generic item-use, the handler returns
`ctx.ai_reply or "<short authored fallback>"`. The model's one-liner gives
the moment texture; the fallback exists so a missing API key, an empty
reply, or an off-route player turn still gets an in-world sentence.

This remains the rule for incidental items whose prose is not narratively
load-bearing. The circuit breaker, matches, light switch, and fireplace are
exceptions: together they carry the Act I reopening ritual, so their authored
lines now win on every path.

| Mode | Where the prose comes from | Where in code | When it applies |
|------|----------------------------|---------------|-----------------|
| Intent parsing only | Hard-coded `feedback="..."` in the handler | Story-beat branches (e.g. `phone`, `camera feed`, `sauna stove`, `bed`, `window`, `mug`, `nika`) | All story-critical beats |
| Fallback flavour | `ctx.ai_reply or "<authored fallback>"` | Generic item-use branches | Off-script, mechanical, ambient |

## The story-critical beat list

Under the authored-beats rule in `AGENTS.md`, these are the beats that must
use the **intent parsing only** mode; this doc owns the list. Each one is tied to a `WorldState` gate flag and to a fixed
piece of authored prose.

| Beat | Act | Gate flag(s) | Handler |
|------|-----|--------------|---------|
| Reopening ritual | I | `reopening_done` | `story/arrival.py`, called from evening fire, first voicemail, real mug or meal; independent of optional chores |
| Voicemail | I | `voicemail_heard` | `actions/use_handlers/phone.py` |
| Camera feed | I | `footage_reviewed` | `actions/use_handlers/act_one.py` |
| Sauna | I | `sauna_used` | `actions/use_handlers/act_one.py` |
| Meal and bed | I | `evening_meal`, `first_morning`, `slept_cold`; sleep gated on voicemail and frames only | `actions/use_handlers/act_one.py`, `story/arrival.py` |
| Morning departure | II | `morning_started` | `map.py` movement out of the bedroom, `story/arrival.py` |
| Reunion: arrival → tended → seated | III | `reunion_stage` | `actions/use_handlers/false_cabin.py` — `use_nika` |
| Reunion: seated → complete (the blue mug) | III | `reunion_stage = "complete"` | `actions/use_handlers/false_cabin.py` — `use_mug` |
| Act III tells (frost / knuckles / smile) | III | `wrongness.has(AnomalyID.X.value)` at `complete`; missing tells land before consent | `story/evening.py`, used by `actions/use_handlers/false_cabin.py` and `map.py` |
| Consent-door beat | III | `consent_given`, `reunion_stage = "consented"` | `map.py` — `_consent_door_beat` |
| Bed / memory aloud | III→IV | `reunion_stage = "bedded"`, `MEMORY_ALOUD` | `actions/use_handlers/false_cabin.py` — `use_mattress` |
| Night seams | IV | night-seam anomalies; missing seams land before recognition | `story/night.py`, used by `map.py` look/listen and the phone/false-cabin use handlers |
| Recognition (the knowing) | IV | `recognition`, `reunion_stage = "night"` | `game/story/night.py` — `maybe_finish_the_knowing` |
| Dawn (the offer) | V | `reunion_stage = "dawn"` | `actions/wait.py` |
| Refuse (The Escape) | V | `ending = "escaped"` | `actions/refuse.py` |
| Accept (stayed) | V | `ending = "stayed"` | `actions/accept.py` |
| Walk out / arrival home | V | `coda_stage = "home"` | `map.py` — walk-out beats, `_arrive_home` |
| Coda: call, scraping, the final wait | Coda | `coda_stage` | `actions/use_handlers/phone.py`; `actions/wait.py` |

(The act labels above match the comments in `world_state.py`, `map.py`,
`anomalies.py`, the `refuse.py` / `accept.py` headers, and the dev seeds.
Match this labelling when adding new beats.)

What these beats share:

- They appear in `WorldState` as gate flags or stage literals.
- They have **fixed authored prose** written into the handler that fires
  them.
- They are the moments the player will quote back at you when describing
  the game. The model must not paraphrase them.

Non-empty authored feedback also retains priority after event listeners run in
`turn.take_turn`. Quest updates cannot erase its narration. Empty movement
results still allow the cutscene channel to supply the scene.

## The anti-pattern: dual narration drift

This pattern is wrong in a story-critical handler:

```python
# DON'T do this for a story beat.
return ActionResult.success_result(
    feedback=ctx.ai_reply or "Nika's voice. Terse, strained, not hers...",
)
```

The `or` looks defensive — "use the model if it gave us something, otherwise
fall back" — but for a story beat it inverts the priority. The model's reply
is almost always non-empty, so the authored prose only ever fires when the
API is down or the cache is cold. The canonical voicemail line becomes the
fallback, and the model gets to write the scene the rest of the time.

That is **dual narration drift** — the same beat narrated two different
ways depending on a model's mood. It is a hard rule in `AGENTS.md`: authored
story beats are canonical prose. Do not reintroduce it.

The correct shape for a story beat is unconditional:

```python
return ActionResult.authored(
    feedback=(
        "You open the voicemail. Nika's voice. Terse, strained, not hers.\n"
        # ... rest of authored prose ...
    ),
)
```

The handler does not read `ctx.ai_reply` at all on the story-beat branch.
The model parsed *use the phone* — its job is done.

## Where the rule does **not** apply

The intent-parsing-only rule is for story-critical beats. Off-script
interaction can and should use AI flavour. This is the texture layer:

- **Generic item-use.** Using a non-story item, or using a story item in a
  state where it has no scripted beat. The `ctx.ai_reply or "<fallback>"`
  pattern is fine here. The Act I breaker, matches, light switch, and fireplace
  are no longer examples because the reopening ritual is authored.
- **Ambient verbs.** Throwing a stone, kicking a door, climbing on the
  furniture. The model is welcome to narrate it diegetically; the action's
  fallback ensures something in-world still lands if the model is silent.
- **Exploration prose where no room has authored a specific response.** If
  the room's `description_fn` or `wrong_description_fn` does not surface
  authored prose for a particular look or action, the model may carry the
  moment. The general `Use` branch at the bottom of the handler accepts
  `ctx.ai_reply` for this texture. Without one, it returns a grounded result:
  rope and key have object-specific lines, while other items are tested and
  leave the room unchanged.

The rule is positional, not blanket. Off-script flavour is a feature; it is
the texture that makes the world feel responsive between the authored
beats. Just keep it on the off-script side of the line.

## Authoring guidance

### Writing a new story-critical handler

Follow the canonical pattern in `actions/use_handlers/false_cabin.py` — the
`window`, `mug`, and `nika` handlers are the model:

1. **Branch by state.** The handler reads the relevant `WorldState` flag
   (`reunion_stage`, `world_layer`, an Act I bool) and dispatches to a
   stage-appropriate branch. Every reachable state has its own branch.
2. **Return authored prose in every branch.** Each branch's
   `ActionResult.authored(...)` carries fixed `feedback="..."` text and
   blocks model-proposed effects. Do not reference `ctx.ai_reply`. Do not fall
   back to the model.
3. **Mutate state inline.** If the beat advances a gate flag, do it in the
   same code path as the prose, not in an `on_enter` or ambient handler.
   This is the "silent flag flips for narrative beats" anti-pattern in
   `AGENTS.md` — flags that change must be narrated in the same beat.
4. **Request shared effects deliberately.** If a downstream listener or the
   shared turn core genuinely needs a signal, return a payload-complete typed
   request from `game/events/requests.py`. Do not add labels for story branches
   that are already characterised by narration and direct state.
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
  appears in. See the hard rules in `AGENTS.md` for what keeps model output
  in-world.
- Mechanics docs may name the Lyer plainly (per `AGENTS.md`). Player-facing
  prose — authored or AI — must not.

## Code anchors

- `game/ai_interpreter.py` — compatibility facade and single public
  `interpret()` entry point.
- `game/ai/types.py` — `Intent` dataclass (`action`, `args`, `confidence`,
  `reply`, `effects`).
- `game/ai/rules.py` — deterministic handling for trivial commands.
- `game/actions/base.py` — the `Action` ABC, `ActionContext` (the
  `ai_reply` property surfaces `intent.reply`), and `ActionResult` with
  `feedback`, typed `requests`, and `model_effects` policy.
- `game/actions/inventory.py` — `TakeAction`'s `person` branch returns
  unconditional authored prose, layer- and ending-gated to agree with
  `use_handlers/false_cabin.py`'s `nika` handler. Every other branch uses
  `ctx.ai_reply or "..."`.
- `game/actions/use_handlers/` — the canonical references behind the
  registry-facing `UseAction`. Story-critical handlers
  (`circuit breaker`, `matches`, `light switch`, `fireplace`, `phone`, `camera feed`, `sauna stove`, `bed`, `window`, `mug`, `nika`,
  `mattress`, `tins`) return unconditional authored prose. The final
  generic branch still accepts `ctx.ai_reply` for incidental objects, with
  grounded authored consequences when the model is silent.
- `game/actions/refuse.py`, `game/actions/accept.py` — the dawn endings;
  authored prose only, on every branch including the failure modes.
- `game/actions/wait.py` — the dawn turn and the coda beats; authored on
  the story branches, `ctx.ai_reply or` on the generic one.
- `game/map.py` — `_consent_door_beat`, the walk-out beats, and
  `_arrive_home`; authored prose firing alongside the state mutation.
- `game/story/night.py` — the recognition scene, appended to the
  observation that earned it.
- `game/game_engine.py` — orchestration: `interpret()` → `Intent` →
  `ActionRegistry` → `Action.execute()` → `ActionResult`.
- Related mechanic docs:
  - `AGENTS.md` hard rules — what keeps model output diegetic when fallback
    flavour fires.
  - `docs/game_mechanics/reunion-mechanic.md` — the canonical example of a
    stage-branched story-beat handler in `actions/use_handlers/false_cabin.py`.
  - `docs/game_mechanics/recognition-and-refusal.md` — the Act III–V beats
    that depend on this rule.
