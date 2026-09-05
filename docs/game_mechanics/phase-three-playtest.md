# Phase 3 playtest: camera errand and forest

Stop for Alex's playtest/read at this phase. The false-cabin dependency audit,
coda pass and remaining prop cleanup are still Phases 4–6.

For a quick playable start, enter `load act1_end`. Elli has just woken in the
bedroom after a warm, powered evening with the sauna. Use `out` to come through
to breakfast, then `grounds` for the tracks and camera. If a disk slot already
uses that seed name, it takes precedence; rename the slot or start a fresh game.

The direct route is:

```text
load act1_end
out
grounds
test camera
replace battery
compare images
north
north
north
back
```

`use camera` advances the same three stages. After replacement, `use phone` or
`use camera feed` can make the comparison too. No look/listen is required to
find the forest tells. The last `back` triggers the encounter and flight into
the false cabin. Read/play through that arrival, then pause.

Useful departures from that route:

- Before finishing the job, try `north` from the grounds and the shore climb
  (`west`, `east`, `north`). Both should hold for the same reason.
- With mains power, revisit the konttori before and after replacing the battery.
  The fourth feed returns before the comparison opens the woods.
- Leave and return during the repair, save/load each stage, or use the phone
  while it is showing the local picture.
- From Dead Pines, go south twice, then return north twice. Elli should remember
  passing the hare without another encounter with it. The missing path is one
  further step north.
- For a cold, dark start, begin a fresh game: `north`, `cabin`, `use phone`,
  `use phone`, `bedroom`, `use bed`, `cabin`, `grounds`. The same errand follows;
  neither maintenance nor the direct phone connection needs mains power.

The retained offline scenarios include the ordinary and cold full stories,
`act2_camera_stages`, and the encounter before/after a save. Run them with
`python -m tools.playtest_runner`; reports retain the exact rendered text.
The test suite also carries all eight power/fire/sauna combinations through
both endings, checks older disk saves and resumes each camera stage through
the embedded engine.

Read for the reason Elli keeps going: a small maintenance job becomes a check
of the ground at a nearby tree, then the deterioration draws her far enough to
find the old path missing. The repair should feel practical, the hare singular,
and the decision to turn back should bring the encounter without a hidden
attention checklist.
