# vn/assets — background art slots

This proof of concept ships with **procedural CSS/SVG "plates"** standing in
for finished backgrounds (see `PLATES` in `../engine.js`). The plates exist so
the composition, pacing, and UI weight can be judged now, before any art is
generated.

## Dropping in real art

Each scene in `../story.js` sets a `bg` through the `artBg()` helper, which
points at `assets/<type>.webp`, e.g.:

```js
bg: artBg("drive_dusk")
```

Drop `drive_dusk.webp` into this directory and the scene will use it if the file
loads, falling back to the procedural plate otherwise. To use a different file
or extension, override the `image` path:

```js
bg: { type: "drive_dusk", image: "assets/drive_dusk.jpg" }
```

So you can re-skin one slot at a time without touching the engine.

### Recommended

- **16:9 landscape**, ~1600×900 or larger. The lower third is covered by the
  dialogue scrim — keep it dark / empty (the doc asks for negative space there).
- `.webp` or `.jpg`. Dark, muted, still.
- The scene graph is already wired to these `.webp` filenames, matching the
  current `type`s:
  `drive_dusk`, `cabin_interior_dark`, `cabin_interior_stove`,
  `window_night`, `consequence_quiet`, `consequence_wrong`.
- If a plate is supplied as `.jpg`, update the corresponding `image` path in
  `../story.js`.

### Art direction

The leading style (from the design doc) is gothic-ink + painterly realism:
muted Nordic palette, deep shadow, no figure, no monster — dread from
composition and silence. The doc's full image prompt lives in
`~/obsidian/Projects/the-cabin/the-cabin-visual-novel-mode.md`.

Use the same negative constraints for every plate: no figure, no visible
monster, no weapons, no blood, no skulls, no text, no logo, no UI, no bright
fantasy colours, no comic-book exaggeration. Keep the lower third dark and
quiet for the dialogue scrim.

### Plate prompts

#### `drive_dusk.webp`

Dark illustrated visual novel background for a quiet psychological horror story
set in rural Finland. A narrow gravel driveway at cold dusk leads from a stopped
rental car toward a small old wooden cabin, with dense Finnish pine and birch
forest pressing in around the route. The car should be visible but secondary,
low or near the edge of frame, so the plate can support both the arrival and the
walk to the door. Black pine trunks and pale birch branches lean inward. The
cabin waits ahead, partly obscured by trees, ominous but understated. Gothic ink
illustration with painterly realism, fluid brushwork, fine scratchy line detail,
layered ink shadows, and subtle watercolour tonal variation. Muted palette:
black, cold grey, dirty pine green, bone-white birch bark, faint weathered brown
wood.

#### `cabin_interior_dark.webp`

Dark illustrated interior of a small Finnish cabin at night, unlit and cold. Dry
timber walls, rough floorboards, a simple table, an enamel sink, and a small
window showing only black outside. The room should feel real but sparse, with
objects half-lost in shadow and a low dark lower third for dialogue. Gothic ink
and painterly realism, soft transitions, scratchy line detail, cold grey-blue
darkness, old wood, dust, still air.

#### `cabin_interior_stove.webp`

Same small Finnish cabin interior, now lit only by a low iron stove. Warm orange
firelight pools from the lower left, throwing a long wrong shadow across the
wall. The window is a black mirror. The room remains mostly dark, with the lower
third quiet and uncluttered. Gothic ink with painterly realism, restrained
firelight, deep layered shadow, scratchy timber detail, no cosy glow.

#### `window_night.webp`

A cabin window at night seen from inside. The glass fills the frame, divided by
old dark muntins. Outside, Finnish pines and pale birches stand too close, their
trunks leaning in. Breath fog softens part of the glass. The room around the
window is almost black. Wide 16:9 frame, lower third dark. Gothic ink, painterly
realism, cold grey-green palette, silence, watchfulness.

#### `consequence_quiet.webp`

Grey morning inside the same cabin after a sleepless night. The cold stove, the
door, and the small window sit in dull dawn light. Nothing is overtly wrong, but
the room feels emptied out and patient. Keep the lower third dark and simple.
Gothic ink and painterly realism, muted ash grey, old timber, soft bleak light,
fine scratchy details.

#### `consequence_wrong.webp`

Inside the cabin at night, but the outside has come too close. Through the small
window, dense Finnish forest presses against the glass where the driveway should
be. Birch trunks are pale and near, pine shadows fill the frame. The room is
barely readable in the dark. Lower third dark and empty. Gothic ink and
painterly realism, deep black shapes, organic silhouettes, cold dread, no
creature shown.
