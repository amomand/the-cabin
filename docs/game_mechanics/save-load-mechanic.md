# Save / Load Mechanic

## Overview

The Save / Load system is the smallest mechanic in the game and the one
most often used during development. The player types `save` or `load`
(optionally with a slot name) and the entire run is round-tripped through
a single JSON file. There is no chapter select, no checkpointing, no
autosave timer — saves only exist where the player asked for them.

The mechanic is diegetic at the surface (a one-line authored reply, never
a system message) and unguarded underneath. The engine does not refuse to
save mid-cutscene, mid-reunion, or in the wrong layer. Whatever state
the player is in is the state that gets written. This is intentional for
playtesting, and it is the same path the dev-seed workflow uses to drop
the player into a known story beat.

## Player commands

The system commands are intercepted before the AI interpreter ever runs.
`InputHandler.parse()` in `game/input/handler.py` recognises them by
first token and routes them as `InputType.SAVE` or `InputType.LOAD`.

| Command | Effect | Default slot |
|---------|--------|--------------|
| `save` | Save to `autosave` | `autosave` |
| `save NAME` | Save to a named slot | — |
| `load` | Load from `autosave` | `autosave` |
| `load NAME` | Load from a named slot | — |
| `restore` | Alias of `load` | `autosave` |
| `restore NAME` | Alias of `load NAME` | — |

The slot name is taken from `tokens[1]` of the input, lowercased. Anything
beyond the second token is ignored. The shortcut is greedy on the first
token — `save` followed by anything is always treated as a save, never as
a creative game action.

### Diegetic feedback

The engine never prints "Saved." or "Game loaded." Both paths return a
single authored line in `game_engine.py`:

| Outcome | Line |
|---------|------|
| Save succeeded | *"You fix this moment in your mind. The room holds still around it."* |
| Load succeeded | *"For a moment the room slips. When it settles, you are somewhere remembered."* |
| Load failed (no such save) | *"You reach for that thread and find nothing tied to it."* |

These are the canonical strings. The `GameEngine._save_game()` and
`_load_game()` methods write them to `_last_feedback`, which the render
manager surfaces alongside the next room redraw. There is no separate
"save failed" branch — `save_game()` itself does not currently return a
failure path beyond raising on the filesystem.

## Slot model

- **Slots are named files, not numbered.** Each unique slot name is one
  file. There is no slot count and no UI for picking a slot.
- **The default slot is `autosave`.** Typing bare `save` or `load`
  reads/writes `saves/autosave.json`. There is no automatic autosave
  trigger anywhere in the engine — `autosave` is just the default
  *name*, not an automatic behaviour.
- **Saves overwrite silently.** `save_game()` opens the file for writing
  and dumps over whatever is there. There is no confirmation prompt.
- **Slot names are sanitised.** `SaveManager._get_save_path()` strips
  every character that is not alphanumeric, dash, or underscore. If the
  result is empty, the slot falls back to `"save"`. Two distinct inputs
  that sanitise to the same name collide silently.
- **The save directory is `saves/`** relative to the working directory.
  It is created on `SaveManager` init if missing.

## What is serialised

`GameState.to_dict()` in `game/game_state.py` is the single
serialisation entry point. It writes only the fields below; everything
else (`last_feedback`, `is_running`, the AI cache, render state) is
transient and discarded.

### `player`
- `health` (int)
- `fear` (int)
- `inventory` — list of item names; on load, names are looked up against
  `map.items` and any unknown name is dropped.

### `map`
- `current_room_id` (str)
- `visited_rooms` — list of room IDs.
- `current_room_been_here_before` (bool) — drives whether the next
  render uses the first-visit prose or the return prose.
- `room_items` — mapping of room ID to the item names currently in that
  room, so taken and dropped items survive a load instead of snapping
  back to the fresh `Map`'s defaults. Restored authoritatively on load;
  unknown item names are dropped. Saves written before this field
  existed load via a fallback that strips restored inventory items from
  their default rooms (no duplication), but dropped items cannot be
  recovered from such saves.

### `world_state` — full `WorldState.to_dict()`
All explicit fields plus any `_custom_flags` ad-hoc keys:

| Field | Type | Purpose |
|-------|------|---------|
| `has_power` | bool | Cabin power state. |
| `fire_lit` | bool | Act I gate. |
| `voicemail_heard` | bool | Act I gate. |
| `footage_reviewed` | bool | Act I gate. |
| `sauna_used` | bool | Act I gate. |
| `first_morning` | bool | Act I gate; required for the Act II climax. |
| `lyer_encountered` | bool | Set by the Act II climax. |
| `recognition` | bool | Set by the Act IV correction-turn. Not cleared by `exit_wrong_layer()`. |
| `world_layer` | `"real" \| "wrong"` | Active layer. |
| `reunion_stage` | `"none" \| "arrival" \| "seated" \| "complete"` | Act III stage machine. |
| `wrong_outside_seen` | bool | Act III pivot one-shot. Cleared by `exit_wrong_layer()`. |
| `ending` | `"none" \| "accepted" \| "refused"` | Act V resolution. Persisted. |
| `wrongness` | `WrongnessLog` | Ordered list of observed anomalies (id, description, acknowledged, seen_at). Round-trips via its own `to_dict`/`from_dict`. |
| `_custom_flags` (flattened) | dict | Dynamic / quest-set flags. Merged into the top level on save; anything unknown on load goes back into `_custom_flags`. |

### `quests`
- `active_quest_id` (str or null)
- `completed_quests` (list of quest IDs)
- `updates` — mapping of quest ID to its fired update entries
  (`event_name`, `text`, `timestamp`), so the held-thought view keeps
  its update history after a load.

On load, every registered quest's `status` is set authoritatively:
`ACTIVE` for `active_quest_id`, `COMPLETED` for anything in
`completed_quests`, `INACTIVE` otherwise. Without this, a loaded active
quest would never update or complete, and a completed quest could
re-trigger.

### `cutscenes`
- `played_ids` — the first 50 characters of each played cutscene's
  text. Restored on load via `CutsceneManager.set_played_ids()`, which
  is authoritative: cutscenes not in the saved set are reset to
  unplayed.

### What is **not** saved

- The AI interpreter's LRU cache.
- Pending events on the bus, or any in-flight `ActionResult`.
- Anything in `GameState` marked transient (`last_feedback`,
  `is_running`).

## On-disk format

JSON, UTF-8, two-space indent, `ensure_ascii=False` (so the prose round-
trips its punctuation untouched).

Top-level shape:

```json
{
  "version": 1,
  "timestamp": "2026-05-14T10:11:12.345678",
  "slot_name": "autosave",
  "game_state": { /* GameState.to_dict() */ }
}
```

- `version` — `SaveManager.SAVE_VERSION`. Currently `1`. On load, a save
  with a *higher* version is treated as unloadable (returns `None`).
  There is no migration path for older versions; the field exists so a
  future shape change can refuse to load old saves cleanly.
- `timestamp` — `datetime.now().isoformat()` at save time. Used only to
  sort `list_saves()` newest-first.
- `slot_name` — the slot name as passed to `save_game()` (lowercased by
  the input parser, but otherwise un-sanitised at this stage; may differ
  from the sanitised filename). Stored redundantly with the filename so
  `list_saves()` can report it without parsing the path. Sanitisation
  (alphanumeric + `-_` only) is applied inside `_get_save_path()` and
  affects the **filename**, not the stored field.
- `game_state` — everything from `GameState.to_dict()` above.

File path: `saves/<sanitised-slot-name>.json`. The `saves/` directory is
git-ignored at the repo root.

## Load semantics

`SaveManager.load_game()` returns the saved `game_state` dict, or
`None` if the file does not exist, the JSON is malformed, or the file's
`version` is greater than `SAVE_VERSION`. The engine treats all three
the same way: it surfaces the failure line above and leaves the run as
it was.

When the dict is present, `GameEngine._load_game()` calls
`GameState.from_dict()`, which mutates the existing `Player`, `Map`,
`QuestManager`, and `CutsceneManager` in place rather than constructing
new ones. The current room is set via `Map._set_current_room_by_id()`,
the visited-rooms set is replaced, and the world state is rebuilt via
`WorldState.from_dict()`. The engine then clears `_last_room_id` to
force a full room redraw and writes the diegetic feedback line.

### Validation on load

`WorldState.from_dict()` enforces literal-string fields defensively:

- Unknown `world_layer` values coerce to `"real"`.
- Unknown `reunion_stage` values coerce to `"none"`.
- Unknown `ending` values coerce to `"none"`.

Any unknown top-level key falls into `_custom_flags`. Boolean fields are
not strictly type-checked at load (`validate()` exists for explicit
calls but is not invoked by the load path).

### Fallback: loading a dev seed by name

If `load NAME` finds no file but `NAME` matches a key in
`game.devtools.seed_saves.SEEDS`, the engine builds the seed fresh and
loads its `to_dict()` directly. This is what makes `load act3_arrival`
work even when `saves/act3_arrival.json` is not present on disk.

### What load does not do

- Does not roll back any side effects of the in-flight turn that issued
  the `load`. The command is processed before the AI; loading replaces
  state before any action runs.
- Replaces inventory entirely. `from_dict()` calls
  `player.inventory.clear()` unconditionally before repopulating from
  the save list. Items present in the current run but absent from the
  save are dropped; the result is replacement, not merge. Room item
  placement is replaced the same way from `room_items`.

## Dev seed workflow

`game/devtools/seed_saves.py` is the supported way to jump to a known
story beat for playtesting. It writes pre-built saves to `saves/dev/`,
which is separate from the player-facing `saves/`.

| Command | Effect |
|---------|--------|
| `python -m game.devtools.seed_saves` | Regenerate all seeds into `saves/dev/`. |
| `python -m game.devtools.seed_saves list` | List the available seed names and their one-line docstrings. |
| `python -m game.devtools.seed_saves generate` | Same as the default — regenerate all. |
| `python -m game.devtools.seed_saves use NAME` | Copy `saves/dev/NAME.json` into `saves/NAME.json` (regenerating it first if missing). The in-game `load NAME` then picks it up. |

Each seed is a `() -> GameState` builder that chains from the previous
beat. The current set, in story order:

| Seed | Beat |
|------|------|
| `act1_end` | Morning after sauna and bedroom sleep. All Act I beats fired. Ready to follow the forest route. |
| `act2_mid` | Midway through the Act II forest approach. Two anomalies logged, wrongness threshold not yet met. |
| `act3_arrival` | Just fell through the wrong cabin door. `lyer_encountered`, `world_layer = "wrong"`, `reunion_stage = "arrival"`. |
| `act3_seated` | Settled at the table. `reunion_stage = "seated"`. Coffee in front of her. |
| `act4_recognition` | Correction-turn fired. `reunion_stage = "complete"`, `wrong_outside_seen`, `recognition`, `CORRECTION_TURN` tell logged. Refuse / accept available in Act V. |
| `near_death_health` | Health at 2 in the forest (`wilderness_start`). One wildlife attack — or any narrated harm — crosses the fade threshold. For exercising the death flow. |
| `near_death_fear` | Fear at 98 in the wrong layer (`cabin_main`, reunion arrival). One more tell or fright tips into collapse. For exercising the death flow. |

The last two are not story beats — they exist to put the player one nudge
from death so the closing-line flow (see `death-mechanic.md`) is quick to
reach on both surfaces.

Seeds set state directly on `WorldState` and call the helper
`enter_wrong_layer()` where the canonical transitions belong — the
single supported exception to the "no direct state pokes" rule called
out in `reunion-mechanic.md`. New seeds belong in this file, not as
inline state setup in test fixtures.

## Edge cases and limitations

These are the rough edges as the code stands today. They are documented
here so future authors can decide deliberately whether to keep them.

- **No save guard anywhere.** The player can `save` during a cutscene,
  mid-reunion, in the wrong layer, on the Act V threshold, or at any
  fear / health level. The resulting save is a faithful snapshot of
  whatever flags are currently set. This is fine for playtesting and
  for the design's "you can step out and come back" stance. If a future
  beat needs to be uninterruptible, the guard belongs in
  `GameEngine._save_game()`, not in `SaveManager`.
- **Inventory items unknown to the current `Map`** are silently dropped
  on load. If an item is removed from `map.items` in a future version
  but appears in an old save's inventory, the load succeeds without
  it.
- **Save-version handling is one-way.** A save with a higher version
  than `SAVE_VERSION` refuses to load (returns `None`, surfaces the
  "no thread" failure line). There is no downgrade path and no
  migration shim for older versions.
- **Slot name collisions are silent.** `save NIKA` and `save nika!!!`
  both sanitise to `nika` and write the same file.
- **`GameEngine` is the canonical loop.** Runtime save/load behaviour
  belongs in `game/game_engine.py` and should restore through
  `GameState.from_dict()`.
- **`SaveManager.list_saves()` and `delete_save()` exist** but are not
  wired to any player command today. They are available for tests and
  for any future save-browser UI.

## Authoring guidance

### Add fields to `WorldState`, not `_custom_flags`

If a new beat needs a flag that should round-trip through saves, add it
as an explicit field on `WorldState` with a default value and an entry
in the `known_fields` set in `from_dict()`. The `_custom_flags` escape
hatch round-trips correctly, but explicit fields are typed and show up
in IDE autocomplete; new story state belongs there.

### If a new beat needs literal-string validation, mirror the existing pattern

`world_layer`, `reunion_stage`, and `ending` each have a defensive
clause in `from_dict()` that coerces unknown values back to the safe
default. Any new `Literal[...]` field should do the same. The point is
that a malformed or stale save should not crash the load — it should
land in a safe state and let the player keep playing.

### Bump `SAVE_VERSION` only on incompatible changes

Adding a field with a sensible default is not an incompatible change —
old saves will load and pick up the default. Renaming a field, changing
its semantics, or removing one are incompatible changes; those warrant
a `SAVE_VERSION` bump and an explicit decision about how (or whether)
to migrate.

### Do not write a save-blocking guard for narrative reasons alone

The current design lets the player save anywhere. A guard that refuses
to save mid-cutscene would need a diegetic failure line and a clear
authored justification. Per `CLAUDE.md`, the failure must be narrated,
not labelled. If you can't write the in-world line, you probably should
not add the guard.

## Code anchors

- `game/persistence/save_manager.py` — `SaveManager`, `SaveInfo`,
  `SAVE_VERSION`, slot path sanitisation, JSON write/read, version
  gate, `list_saves()`, `delete_save()`.
- `game/input/handler.py` — `InputHandler.parse()`: `SAVE_COMMANDS`,
  `LOAD_COMMANDS` (`load` and `restore`), slot extraction.
- `game/game_engine.py` — `_save_game()`, `_load_game()`, the diegetic
  feedback lines, the seed-name fallback in load, the forced room
  redraw.
- `game/game_state.py` — `GameState.to_dict()` / `from_dict()`: the
  serialisation shape, the in-place restore of `Player`, `Map`,
  `QuestManager`, `CutsceneManager`.
- `game/world_state.py` — `WorldState.to_dict()` / `from_dict()`:
  literal-string coercion, `_custom_flags` round-trip,
  `WrongnessLog.to_dict()` / `from_dict()`.
- `game/devtools/seed_saves.py` — `SEEDS` registry, builder chain,
  `generate_all()`, `use_seed()`, CLI surface.
- Related mechanic docs:
  - `docs/game_mechanics/wrongness-mechanic.md` — what's inside the
    persisted `wrongness` log.
  - `docs/game_mechanics/world-layers-mechanic.md` — what
    `enter_wrong_layer()` and `exit_wrong_layer()` change in the
    saved state.
  - `docs/game_mechanics/reunion-mechanic.md` — the `reunion_stage`
    field that round-trips through save/load.
  - `docs/game_mechanics/recognition-and-refusal.md` — why
    `recognition` and `ending` persist and why they are not cleared by
    `exit_wrong_layer()`.
