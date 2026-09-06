# Save and load

Named disk slots preserve a run for player use and playtesting. They are separate
from the automatic mobile checkpoints described in the
[iOS client contract](../architecture/ios-client.md). This page owns disk-slot
compatibility; it does not duplicate the fields and stages owned by story mechanics.

## Commands and storage

`save [NAME]`, `load [NAME]` and `restore [NAME]` are intercepted before the
interpreter. Bare save/load uses `autosave`, which is a slot name, not an engine
autosave timer. `saves` lists slots; `delete save NAME` (or `remove save NAME`) removes one. Shared behaviour
and authored feedback live in [game/save_commands.py](../../game/save_commands.py).
Listings omit filesystem timestamps, although timestamps sort the files newest first.

Save/load take the lowercased second token as the name and ignore later
tokens; deletion takes the third token after `delete save`, defaulting to
`autosave` when absent. Filenames retain only alphanumeric characters, dash and underscore,
falling back to `save` when empty. Names that sanitise identically collide and
writes overwrite without confirmation. The original supplied name remains in
the JSON metadata. Files are UTF-8 JSON under `saves/` by default; the directory
is created on first write. [Server surfaces](../architecture/server-surfaces.md#saves)
owns the temporary/durable remote directories and retention policy.

There is no narrative save guard in the engine. Supported save commands capture
the current state, including the wrong layer and partially completed beats;
adding a story-based refusal would require an explicit design decision and
in-world feedback. Input availability during an overlay remains a surface concern.
Filesystem write errors can raise; there is no shared narrated write-failure path.

## Restore contract

[GameState](../../game/game_state.py) defines the payload: player stats and
inventory, room/visit/item placement, world state, quest status/update history
and cutscene played identities. The disk wrapper in
[SaveManager](../../game/persistence/save_manager.py) adds `version`, `timestamp`
and `slot_name`. `SAVE_VERSION` is currently 1. A higher version, unreadable
file or malformed JSON returns no payload. This is not comprehensive validation
of arbitrary JSON shapes.

An unavailable payload falls back to the named development seed if one exists.
A valid disk slot therefore takes precedence over a seed; rename or delete it
to reach the fresh seed. If neither resolves, the run remains unchanged.

Restore replaces saved component state, with a partial-placement limitation:

- Inventory and saved room placements are authoritative. Unknown item names
  are dropped. Rooms omitted from a saved placement map retain their existing
  contents, which are defaults only when loading into a fresh map. For example,
  removing the cabin's matches before loading a slot that omits `cabin_main`
  leaves them absent. This dependence on the previous run is a limitation, not
  the intended restoration contract: [follow-up #276](https://github.com/amomand/the-cabin/issues/276)
  tracks restoring omitted rooms from fresh-world defaults, reconciled with
  saved inventory to prevent duplication. Slots predating room placements
  remove restored inventory from existing rooms, but cannot recover old
  dropped-item positions.
- Registered quests have status and updates replaced. Unknown quest IDs are
  ignored; if an ID is both active and completed, completed wins. This prevents
  restored quests replaying openings or losing their ability to update.
- Cutscene play history is replaced, including resetting scenes absent from
  the saved set. [Cutscene identities](cutscene_mechanic.md) are stable filenames.
  Very old text-prefix identities match no scene and are ignored, allowing a
  one-time replay before the next save records stable IDs.
- A loaded prompt redraw is a revisit, so it cannot repeat finding the key or
  falling into the false cabin. Surfaces reset their render/overlay state after
  a successful load. Death and ending checks still apply to a restored run.

AI caches, pending events, action results and transient feedback are not disk
slot state. Exact pending-turn/frame recovery belongs to mobile checkpoints.

## Compatibility commitments

[WorldState.from_dict()](../../game/world_state.py) tolerates sparse older disk
state. Unknown layer, reunion, ending and coda literals use their safe defaults;
an unknown camera stage becomes `untouched`. Unknown keys without a leading underscore round-trip through
`_custom_flags`. Booleans are not strictly validated by this disk-load path.
New story fields should be explicit typed fields with defaults and deliberate
load handling, rather than new ad-hoc flags.

The existing migrations retain these promises:

- Missing evening meal and morning-start history inherit `first_morning`.
  Missing reopening history is inferred from a completed first night or the old
  power-plus-fire conditions. Missing `slept_cold` is false; loading never charges
  retroactive cold-night damage.
- Without `camera_stage`, the legacy combined fox/camera tell implies `compared`;
  otherwise the errand is `untouched`. The grounds regain the camera fixture.
  An unfinished old forest position can retreat to complete the job.
- Slots predating reopening history replace movable phone/frame copies with
  the table and monitor fixtures. All disk slots, including those with newer
  evening history, strip obsolete carried-equipment copies from rooms and
  inventory. Ordinary props and dropped locations remain intact. Retained item
  definitions, including unplaced berries, still resolve old names.
- Stable room IDs and anomaly IDs survive changes of display text. In particular,
  `stone_formations` now records the missing path; `CORRECTION_TURN` and
  `wrong_outside_seen` remain legacy compatibility data.
- Already-recognised saves retain the night gate's count-only compatibility
  described in [recognition](recognition-and-refusal.md). Old outdoor coda
  positions can retreat home under that page's route contract.

These repairs are for disk slots. Embedded checkpoints validate their current
schema strictly and reject a noncanonical restoration instead of silently
adopting repaired state. Adding a compatible disk field does not require a
version bump; a rename, removal or changed meaning needs an explicit migration
or rejection decision. Do not remove legacy fields merely because fresh play
no longer sets them.

## Development seeds and verification

The [playtesting guide](../architecture/playtesting.md#dev-seed-saves) owns seed
commands and retained scenario evidence. Builders live in
[game/devtools/seed_saves.py](../../game/devtools/seed_saves.py); they may construct
requested state directly, unlike runtime story handlers. Keep new seed setup
there rather than copying a second builder into each test.

Relevant executable contracts are [disk round trips](../../tests/test_save_load.py),
[return and equipment migration](../../tests/test_return_story.py),
[seed builders](../../tests/devtools/test_seed_saves.py) and
[embedded checkpoint validation](../../tests/server/test_local_engine.py).
