# False evening, walk out and coda

Phases 4–6 of the [playable-story work](../lore/playable-story.md) close the
remaining dependencies after the optional evening and staged camera errand.
The reunion, consent, knowing, refusal and stayed ending retain their plot.
The whole-game perception and substantive room-prose pass remains in
[#269](https://github.com/amomand/the-cabin/issues/269); these changes apply its
contract only to passages needed for the later story.

## Dependencies

| Beat or observation | Required prior action | Result and repeat behaviour |
| --- | --- | --- |
| False-cabin arrival | The forest encounter | The first scene establishes Nika, the open green book and the tended fire. Later attention and loaded redraws recall her waiting; they do not repeat falling through the door. Entering this layer is a fresh arrival even after visiting the real cabin. |
| Early window and tins | Reunion underway | The last evening light is going; dinner has yet to happen. Neither inspection advances the reunion or logs a premature seam. |
| Dinner recollection | `KNUCKLES_BIRCH` observed | The existing ordered evening beat narrates dinner before the hand on the plate. Tins and the room can now recall the meal. No extra dinner flag is needed. |
| Mattress laid | Consent-door beat | The chest remains the preparation cue until using the mattress narrates Nika stacking the fire, postponing tonight's sauna and making the bed. Repeated room attention does not perform that work. Yesterday's sauna choice does not change the line. |
| Phone's dark screen | Bedded or night | Nika hangs the jacket on the peg during the care beat. Later Elli gets the phone from it, tries it and returns it to that pocket before going back to bed. It leaves with the jacket after the refusal. Requests for saved frames use the same stage-aware phone response. |
| Walk out | Refusal | The existing three moves remain one-way. Help names only forward destinations. The head torch is on for the walk and switched off on reaching real daylight. |
| Return home | Final southward step | Grounds and clearing lead to the cabin. They describe the return, without camera maintenance or earlier discoveries. Entry returns the key to her pocket and holds her before the empty hook. |
| Call, packing, scraping, wait | Coda stages in order | The window/phone makes the call; `wait` or `pack` continues packing and starts the scraping; the next wait seats her and completes the ending. The outer-door refusal follows the current stage. |

The false cabin's lamp and tended fire remain independent of real power and
heating. The real coda preserves power and fire history, including a fire lit
after a cold night. It retains the open bed, corked bottle, empty glass and
empty hook. Its unpowered breaker is left alone; lighting or inspecting the
hearth does not restart the first-evening chores. The saved frames do not
reopen the camera errand. The bedroom and konttori remain accessible from the
main room, with the bed and monitor respecting the coda. During the scraping,
listening from either adjoining room retains the sound through the doorway.
Outdoor fire requests have a location-aware refusal rather than describing the
cabin hearth.

`Map.story_route_denial()` is shared by movement and help. After the return,
all grounds and clearing exits except those leading home are held. Older disk
saves made on an outdoor coda detour can retreat towards the cabin; they cannot
go deeper into the woods or restart an outing. No additional coda state is
stored. Once inside, ordinary play cannot return to the grounds and replay
the homecoming.

## Equipment and retained props

`game/story/equipment.py` keeps the phone, frames, key, compass, head torch and
meter addressable separately from movable inventory. The key becomes known
after the clearing arrival (also retained by later dev seeds). Torch, cabin-key
and multimeter aliases resolve through the same context used by both surfaces.
Taking, dropping and throwing known equipment keep it in its authored place.
The meter can test an untouched camera; inspecting it again cannot replace a
battery or compare pictures.

Disk loading removes obsolete equipment copies from inventory and room
placements, including slots already carrying Phase 2 history. Rope, stones,
sticks and ordinary dropped objects retain their saved placements. Current
version-4 embedded checkpoints remain compatible: there is no new stored field
or change to the checkpoint shape. Strict checkpoint validation still rejects
a noncanonical snapshot rather than silently repairing it during adoption.

Rope, stone and stick have reachable generic-use or throwing behaviour, so they
remain available. Berries have no fresh-world placement; their definition is
retained for older disk saves. No source manuscript or published story snapshot
is changed. No unused world-state flag was removed without a demonstrated
compatibility-safe reason.

## Reproduction

Run offline from the repository root:

```sh
python -m pytest -q
python -m tools.playtest_runner
```

`act3_dependencies_and_return` retains stage checks, repeat attention, saves,
equipment use, one-way travel and the coda through completion on both surfaces.
`act1_cold_dark_coda`, `act1_morning_repair_return`, and the ordinary escaped and
stayed paths retain representative complete reads. The parametrised parity
route covers all eight power/fire/sauna combinations through both endings.
`tests/test_return_story.py` covers the remaining sequence and route gaps,
including old coda detours and equipment migration. The parity suite checks the
first false-cabin scene across attention, overlays and loading.

Reports under `reports/playtests/` are local review evidence. Phase 7 still owes
the uninterrupted final whole-story read and closure audit of #264.
