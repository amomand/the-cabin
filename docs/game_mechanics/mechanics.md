# Mechanics reference

Choose the reference for the task; this directory is not a required reading list.
The original mechanics sketch is historical material, retained in Git history,
not a backlog or a description of the current game.

## Authority and reading routes

| Need | Authoritative reference |
| --- | --- |
| Story intent, character knowledge and the canonical ending | The maintainer's Obsidian plotline and prose; [plotline snapshot](../lore/plotline.md) and [published prose snapshots](../../stories/README.md) identify their sources. [Characters](../lore/characters.md), [setting](../lore/environment-setting.md) and [the Lyer](../lore/the_lyer.md) provide supporting interpretation, not alternative beat contracts. |
| Game-side adaptation: site plan, optional choices, persistent objects and revelation timing | [Playable-story bible](../lore/playable-story.md). It owns these decisions; mechanics pages explain the relevant interaction boundaries. |
| Arrival, closer observation and fair discovery | [Perception and room descriptions](perception-and-room-description.md). The bible records what exists and when it can be revealed; this contract owns how attention selects that material. |
| Authored output versus model suggestions | [Narration priority](narration-priority.md); [effects](../architecture/effects.md) owns effect application and turn ordering. |
| Reopening, sleep, first morning | [Evening and first morning](first_morning_miniquest.md), [voicemail](voicemail_miniquest.md), [frames and camera](camera_footage_miniquest.md), [sauna](sauna_miniquest.md). |
| False evening, recognition, endings and return | [Reunion](reunion-mechanic.md), then [recognition and refusal](recognition-and-refusal.md). |
| Anomaly identity and logging | [Wrongness](wrongness-mechanic.md). Arc-specific gates belong to the relevant story mechanic. |
| Layer transitions and overlays | [World layers](world-layers-mechanic.md). |
| Physical interaction and remembered routes | [Items and equipment](item-mechanic.md), [map](map-mechanic.md). |
| Stat consequences and closing a run | [Fear curve](fear-curve.md), [death](death-mechanic.md). |
| Interrupting scenes and held thoughts | [Cutscenes](cutscene_mechanic.md), [quests](quest-mechanic.md). |
| Persistence and compatibility | [Save/load](save-load-mechanic.md); [iOS](../architecture/ios-client.md) owns mobile checkpoint and retry behaviour, [server surfaces](../architecture/server-surfaces.md) owns remote session lifetime and save storage. |
| Running checks or reviewing prose | [Playtesting](../architecture/playtesting.md), [prose review](prose-review-manifest.md). |

The [configuration](../architecture/configuration.md), [event bus](../architecture/event-bus.md)
and [review gate](../architecture/review-gate.md) references cover their own
operating boundaries. The [scheduled playtest review](../architecture/agentic-playtest-review.md)
is a separate workflow, not an ordinary PR gate.

The game has no exposure timer, hunger system, recurring sleep or dream system,
procedural map, combat progression or player journal of anomaly counts. Earlier
sketches of those systems do not authorise adding them. Current work and delivery
history belong in GitHub issues/PRs and the maintainer's dated project handovers.
