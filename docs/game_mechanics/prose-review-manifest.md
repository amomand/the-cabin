# Prose Review Manifest

This is the boundary for a whole-game prose pass. It covers fixed text a player
can encounter in the current game, including prose that frames utility actions.
It does not treat comments, developer-only examples, unused location overviews,
or other non-runtime examples as playable prose. Model-generated replies are
variable; their prompt contract, sanitiser, and evaluation suite are the review
boundary for that channel.

## Rubric

Judge each substantial passage for its intended scene and place in the arc.
Record concrete findings: the reachable state and input, the passage, what fails
and why a change would improve it. These questions guide the judgement:

- **Craft and interest:** exact language, varied cadence, useful detail, and no
  dead or interchangeable sentences.
- **Scene and arc:** does the passage provide the intended familiarity, warmth,
  relief, pressure or dread? Where wrongness belongs, does it grow from concrete
  discrepancies and consequences without naming or explaining the Lyer? Ordinary
  comfort is valuable on its own and must not be dressed in forced menace.
- **Voice and attention:** does language follow Elli's particular attention,
  rather than generic sensory scaffolding or ornamental polish? Repeated
  patterns can prompt a closer read; a construction alone is not a defect.
- **Continuity and discovery:** does it respect the source, the bible's state
  and revelation order, and the [perception contract](perception-and-room-description.md)?
  Arrival and deliberate attention must agree as well as terminal and web.

A passage is ready when it fits the scene and no concrete editorial or
continuity defect remains. Explain material judgement calls; do not demand a
numeric threshold or maximum dread. Follow the close read with an uninterrupted
transcript read so local improvements cannot hide repetition, missing beats or
a broken arc. Critique does not itself authorise rewriting canonical fiction.

## Reachable prose and proof

| Surface | Primary deterministic proof |
| --- | --- |
| Arrival, room descriptions, visible objects, listening, inventory, free-form offline replies, practical help, generic use, dropping, throwing, quest and map framing | `ambient_prose.yaml`, `ambient_interior_prose.yaml`, `weird_input.yaml` |
| Cabin-entry cutscene, Warm Up text, save/load/list/delete text, terminal/browser parity | `both_surfaces_overlays_and_saves.yaml`, `act1_smoke.yaml` |
| Act I evening, camera, voicemail, sauna, first sleep | both full-story scenarios |
| Act II forest, wrongness route, encounter and flight | `act2_climax_forest_route.yaml`, `act2_climax_survives_save_load.yaml`, both full-story scenarios |
| Act III reunion, evening tells, consent door and unusual input | `act3_seed.yaml`, `act3_reunion_weird_input.yaml`, both full-story scenarios |
| Act IV bed, night seams, recognition and accounting | `act4_night.yaml`, both full-story scenarios |
| Act V refusal, one-way walkout, return and complete coda | `act5_walkout_no_return.yaml`, `act1_to_act5_golden_path.yaml` |
| Act V stayed ending from the dawn seed and from the opening | `act5_accept_route.yaml`, `act1_to_act5_stayed_path.yaml` |
| Fear and health closing lines in the real layer | `death_fear.yaml`, `death_health.yaml` |
| Generic branches not economical to reach in a story route | focused tests under `tests/actions/`, `tests/test_game_engine.py`, and `tests/server/test_session.py` |

The playtest runner defaults to every YAML file in `playtests/scenarios/`. A
whole-game pass is not complete until they all pass on their declared surfaces,
the full test suite passes, and the two full-story transcripts have been read in
order against `stories/the-cabin.md` and `docs/lore/plotline.md`.
