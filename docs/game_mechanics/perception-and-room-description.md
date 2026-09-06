# Perception and room descriptions

## Authoring contract

Room entry and deliberate attention serve different purposes. Arrival establishes
Elli's immediate impression and gives her useful reasons to explore. An object
being present is not, by itself, a reason to describe it on every arrival or load.
The room matrix in [the playable-story bible](../lore/playable-story.md) records
physical truth and available material, not a transcript to recite in full.

| Occasion | What the prose should do |
| --- | --- |
| Arrival, return or restored position | Establish place, atmosphere and relevant change through a selective impression. Give enough orientation and salient cues to act. Preserve first-visit versus revisit history. |
| `look` | Reward closer visual attention with room detail that arrival need not enumerate: useful objects, their relationships and visible state. Compose an observation rather than an inventory of equally weighted fixtures. |
| `listen` | Reward deliberate acoustic attention: a faint or intermittent sound, its apparent direction, a rhythm, or an absence that now matters. Respect phase, power, weather and established stillness. |
| Targeted examination or listening | Develop the particular thing the player attends to, within what Elli can perceive and already knows. Supply discoveries through their existing authored actions and gates. |

This is a distinction of attention, not an absolute separation of senses. A
sudden noise, obvious movement or immediate danger can demand attention on
arrival. Ordinary audible details can also help establish a room. More sustained
listening should have something appropriate to add; it must not invent a new
sound merely to avoid repeating an established silence.

Keep exploration fair. An essential object or source of a sound needs a
perceptible cue or a route to discovery through general attention; the player
must not guess an unmentioned object's exact name. Do not require both `look`
and `listen` in every room as a hidden checklist. Preserve the story's existing
automatic discoveries, attention beats and knowledge gates. Moving material out
of arrival prose does not authorise delaying or advancing a revelation.

All descriptions remain true to the current layer, phase, object locations and
prior actions. Repeated attention recalls a completed discovery rather than
performing it again. State correctness constrains what can be said; it does not
require every true fact to be said. Compose connected, bookish paragraphs around
what Elli notices and why it matters, including ordinary warmth where it belongs.
Do not manufacture variety by merely replacing repeated sentence openings.

## Shared implementation and verification

Terminal and web arrivals use `Room.get_description()`. Closer views and ambient
sound live in `game/story/perception.py`, with targeted subjects in
`game/story/targeted_attention.py`. `LookAction` adds movable item descriptions;
wrong-layer overlays retain ownership of their whole scene. Existing
`Map.observe_current_room()` and story handlers own discoveries and callbacks.
No perception history or extra save fields are required.

Both observation actions return authored results, including when a model parses
the input. Model flavour and suggested effects cannot replace the observed
scene. Explicit looking, examining and listening do not operate fixtures,
sleep, or accept coffee. Voicemail playback and saved-image review retain their authored actions;
attention to an existing story tell can still reveal it through its current gate.

For changes here, read an assembled arrival, `look` and `listen` together at the
same reachable state, then repeat attention and reload it. Compare the senses
with each other, not only terminal with web: surface agreement can preserve the
same contradiction. Include a natural-language or targeted route when it can
reach a different response. Keep that evidence in the PR or playtest report;
use permanent tests for behavioural defects, never paragraph shape or prose scores.
