# Narration priority

The model interprets free text into an `Intent`; an action decides what reaches
the player. Story beats, observations and their state changes have authored
responses. Incidental off-script interaction may accept model flavour within
the deterministic world's constraints. That distinction must not depend on
whether the API happens to be available.

## Authored responses

Use `ActionResult.authored(...)` for a story beat and for each of its unavailable
or repeated branches. It returns fixed prose and blocks model-proposed effects.
Do not consult `ctx.ai_reply` on those paths: `ctx.ai_reply or authored_text`
would make the authored scene an offline fallback and let the model rewrite it
in ordinary connected play. This is the dual narration drift prohibited by
[AGENTS.md](../../AGENTS.md).

This covers the reopening and practical fire/power interactions, evidence,
meal, sauna, sleep, camera errand, forest discoveries, the whole false-cabin
arc, both endings, walk out and coda. Their triggers and dependencies belong
to the [story mechanics](mechanics.md), not a second beat inventory here.
Carried equipment has authored use and retention responses too.

Room `look` and `listen` remain authored even without a new discovery. Explicit
attention does not operate a fixture, sleep or accept an offered drink;
existing tell observations may still reveal their gated beat. The
[perception contract](perception-and-room-description.md) owns this distinction.
Outdoor throws also preserve the woods' indifference rather than inventing an
answering knock.

Non-empty authored feedback must survive quest/event callbacks. An empty
movement result may leave narration to the cutscene channel so the flight
appears before the destination room. The exact ordering and model-effect
policy are defined in [effects](../architecture/effects.md).

## Incidental interaction

The generic use branch and other unscripted interactions can return
`ctx.ai_reply or fallback_text` where that flavour cannot establish story truth.
The fallback supplies a grounded consequence when no model reply is available.
An item having no new beat does not automatically make it eligible: equipment,
story fixtures and observations retain their authored state-aware responses.
Use the current handler as the boundary, not an informal list of ambient verbs.

All output follows AGENTS.md's diegetic rule and the scene's register. The split
between authored prose and model flavour is invisible to the player.

## Changing a handler

Branch on the current world state, narrate any change in the same result, and
use the transition helpers for ordered stages. Return a payload-complete typed
request only when shared effect handling or a bus listener needs it. Validate
the reachable model-assisted route as well as the deterministic one: a rule-based
input with no proposed reply or effects cannot expose narration drift.

Implementation anchors: [action results](../../game/actions/base.py),
[use handlers](../../game/actions/use_handlers/), [shared turn](../../game/turn.py)
and [intent interpretation](../../game/ai_interpreter.py). Existing handlers,
focused tests and [playtest seeds](../architecture/playtesting.md#dev-seed-saves)
provide examples without a separately maintained implementation walkthrough.
