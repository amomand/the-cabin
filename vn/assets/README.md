# vn/assets — background art slots

This proof of concept ships with **procedural CSS/SVG "plates"** standing in
for finished backgrounds (see `PLATES` in `../engine.js`). The plates exist so
the composition, pacing, and UI weight can be judged now, before any art is
generated.

## Dropping in real art

Each scene in `../story.js` sets a `bg`, e.g.:

```js
bg: { type: "drive_dusk" }
```

Add an `image` and it will be used **if the file loads**, falling back to the
procedural plate otherwise:

```js
bg: { type: "drive_dusk", image: "assets/arrival.webp" }
```

So you can re-skin one scene at a time without touching the engine.

### Recommended

- **16:9 landscape**, ~1600×900 or larger. The lower third is covered by the
  dialogue scrim — keep it dark / empty (the doc asks for negative space there).
- `.webp` or `.jpg`. Dark, muted, still.
- Suggested filenames matching the current `type`s:
  `drive_dusk`, `cabin_interior_dark`, `cabin_interior_stove`,
  `window_night`, `consequence_quiet`, `consequence_wrong`.

### Art direction

The leading style (from the design doc) is gothic-ink + painterly realism:
muted Nordic palette, deep shadow, no figure, no monster — dread from
composition and silence. The doc's full image prompt lives in
`~/obsidian/Projects/the-cabin/the-cabin-visual-novel-mode.md`.
