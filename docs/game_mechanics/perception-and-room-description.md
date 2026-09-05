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

## Current implementation and remaining work

This contract was agreed during the Phase 3 read. It guides the forthcoming room
prose revision; it is not a claim that every room already meets it.

- Terminal `GameEngine.render()` and web `WebGameSession._render_room()` show the
  shared `Room.get_description()` result on room redraw. They do not append the
  separate item-description list.
- The ordinary authored path in `LookAction.execute()` reuses that description
  with `revisit=True`, then adds `Room.get_items_description()` and any attention
  beat. `revisit` prevents arrival actions being narrated again; it is not a
  separate level of visual detail. Some off-script replies bypass this path.
- `ListenAction.execute()` supports authored attention beats and phase-sensitive
  stillness, with broader indoor/outdoor fallbacks. Room-specific acoustic
  detail is only partially authored.
- The Phase 2 cabin callback in `game/story/real_rooms.py` puts the mug, hook,
  buckets and wine into the shared base description. Consequently they appear
  on arrival despite the separate item-list mechanism. Other new and inherited
  callbacks also assemble too many individual state facts.

The prose pass must decide what belongs to immediate impression, closer looking,
listening and particular examination, then revise the relevant shared callbacks
and action responses together. Use existing deterministic attention handling
where it fits; this contract does not prescribe new state fields or an engine
redesign. Check assembled arrival and attention output across valid warm, cold,
powered, unpowered, revisit and loaded states on both engine surfaces. Judge
whether attention adds useful detail without losing orientation or replaying
beats. Do not add permanent paragraph-shape assertions.
