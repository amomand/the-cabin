# The remembered map

`m` or `map` opens Elli's mental reconstruction of the explored route. Dismissal
returns to the room. Only visited rooms appear, and a connector appears only
when both endpoints are known. The framing and ASCII treatment belong to
[game/map.py](../../game/map.py) and the shared render path; it is not an
inventory map or a surveyed floor plan.

[The bible's site plan](../lore/playable-story.md#3-site-plan) owns room names,
connections and stable IDs. The display must follow it, including the direct
northward forest route, optional shore loop and the konttori's main-room door.
Layer overlays and movement refusals follow [world layers](world-layers-mechanic.md);
the map does not grant access to a route merely because it is remembered.

Verify that newly visited rooms and their connections appear without revealing
unvisited rooms, and that dismissal preserves first-visit/revisit history under
[the perception contract](perception-and-room-description.md). For route or
render changes use [both-surface scenarios](../architecture/playtesting.md).
