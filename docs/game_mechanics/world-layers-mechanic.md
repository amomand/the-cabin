# World layers

The game reuses room IDs across `real` and `wrong` layers. This is not a second
complete map: only the false cabin and its walk-out route are reachable in the
wrong layer. The [bible](../lore/playable-story.md) owns their geography and
physical truth; this page owns transition and overlay behaviour.

## Transition contract

Use `WorldState.enter_wrong_layer()` and `exit_wrong_layer()` rather than
assigning the layer directly. Entry starts the reunion at `arrival` if it has
not begun. Exit clears the reunion stage, `wrong_outside_seen` and
`consent_given`, but retains recognition, ending and coda history. Returning to
the real world is not amnesia. Helpers mutate state only; callers must pair
each transition with its authored narration.

The Act II encounter triggers on a valid attempt to leave `old_woods`, in the
real layer after first sleep and camera comparison, with `FOX_TRACKS`, `HARE`
and `STONE_FORMATIONS` recorded, no previous encounter and no ending. Other
anomalies cannot substitute. It wounds Elli, enters the wrong layer and delivers
her to `cabin_main`. The collision leaves at least one health; authored fear
uses the [fear ceiling](fear-curve.md). The flight narrates through the
[cutscene channel](cutscene_mechanic.md) before the destination room, so the
movement result is intentionally empty.

Refusal sets the escape ending but does not exit the layer. The final step of
the [one-way walk](recognition-and-refusal.md#walk-out-and-coda) calls
`_arrive_home`, exits the layer, lands at the real grounds and sets the coda to
`home` alongside the return prose. The stayed ending never exits the layer.
These are the two runtime layer transitions; do not introduce an ambient flip
without an authored beat.

## Rendering and input

[Room](../../game/room.py) owns the overlay API: `wrong_name`,
`wrong_description`/`wrong_description_fn`, `wrong_exits` and
`wrong_denial_text`. Both surfaces and interpreter context use its layer-aware
name, description and exits. An absent wrong denial falls back to the room's
ordinary denial and then its indoor/outdoor default. Author an appropriate
refusal where the enclosure matters, so an interior cannot answer with a
layer-blind treeline description.

Description functions receive revisit history and can branch on the derived
`WorldState.story_phase()`. They do not advance scenes. Entering the false cabin
is a fresh arrival even if Elli visited the real cabin; attention, overlays and
loaded redraws do not replay falling through its door. Arrival and deliberate
attention follow the [perception contract](perception-and-room-description.md).

The wrong-cabin overlay follows the [reunion](reunion-mechanic.md) and
[night/ending](recognition-and-refusal.md) stages and recalls only discoveries
already narrated. It owns the complete scene, suppressing generic item lists.
[AI context](../../game/ai_context.py) filters wrong-only fixtures out of real
rooms and exposes carried equipment separately. The filter in code is the
inventory definition: the real mug and window have real-cabin interactions,
so their names must not be blanket-hidden with Nika and the false-cabin props.

When changing a layer-specific fixture or route, verify visibility, use,
attention, movement denial and help at the same reachable state. The room
being visible in context does not authorise a story transition. Movement and
help share `Map.story_route_denial()`; restored legacy positions retain the
retreat paths in the coda and camera contracts.
