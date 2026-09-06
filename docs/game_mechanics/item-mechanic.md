# Items and carried equipment

Movable items live in rooms or in the player's inventory. Taking an item removes
it from its room and puts it in the inventory; dropping it reverses that move.
Both locations survive disk saving and loading. General `look` appends visible
item descriptions where the authored scene allows them. Room arrival follows
the [perception contract](perception-and-room-description.md).

The phone, saved frames, key, compass, head torch and meter are carried story
equipment. They remain available to sensible input without a second movable
copy in the inventory. The key is found on arrival at the clearing. `use key`
checks it in her pocket; unlocking is part of the authored arrivals, with no
separate locked-door puzzle. Equipment cannot be dropped or thrown away.
[game/story/equipment.py](../../game/story/equipment.py) owns names and aliases,
including torch, cabin-key and multimeter input. Taking, dropping or throwing
known equipment retains its authored location. The meter can test an untouched
camera; further inspection cannot replace the battery or compare pictures.
[Save/load](save-load-mechanic.md#compatibility-commitments) owns migration of old copies.

## Traits and fixtures

| Trait | Behaviour |
| --- | --- |
| `carryable` | May enter movable inventory. |
| `usable` | May be used through its handler. |
| `throwable` | May be thrown if carried. Indoor throws leave it in the room. |
| `weapon`, `flammable`, `edible`, `cursed` | Properties available to action handling. They do not create a combat, crafting or eating action by themselves. |
| `person` | Represents someone who can be addressed. Never enters inventory, regardless of other traits. Taking Nika gets an authored response appropriate to the layer and ending. |

Fixtures such as the hearth, bed, window and monitor remain in their rooms.
Their authored handlers determine what happens when used, including unavailable
or repeated actions. A fixture's generic item label is not a second source of
story truth. The false cabin suppresses generic item listings; its stage-aware
prose carries the scene.

Rope, stone, stick, firewood and matches retain their reachable roles. The
unplaced berries definition is retained for older saves. The item dictionary
also retains the old key name so saved copies can be recognised and removed
from inventory during migration. Item state does not grant an alternate escape
or change the deterministic story gates.
