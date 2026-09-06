# The false-cabin reunion

The false evening makes care believable before its seams become legible.
Ordinary warmth and competent attention are essential to that deception.
The [plotline](../lore/plotline.md) owns the copy's knowledge limit and the
relationship it cannot perform; the [bible](../lore/playable-story.md) owns props
and revelation timing. This page owns the playable evening's stage and observation
boundaries; [recognition and refusal](recognition-and-refusal.md) continues at night.

## Stages and actions

| Stage reached | Trigger | What it earns |
| --- | --- | --- |
| `arrival` | Enter the wrong layer after the encounter | Nika waiting with the open green book and tended fire. |
| `tended` | `use nika` at arrival | The grip, the unmade-call lie, face cleaned, pupils and ribs checked; jacket hung on the peg. |
| `seated` | `use nika` again | The verdict, chair and offered coffee. |
| `complete` | `use mug` | First mouthful from the whole blue mug; the evening tells become available. |
| `consented` | First `out` after coffee | Remaining evening tells, then the door onto the wrong outside and the choice of the warm room. Elli stays inside. |
| `bedded` | `use mattress` after consent | Fire stacked, tonight's sauna postponed, mattress laid, lamp down and Nika's memory spoken aloud. |

Runtime handlers advance through `transition_reunion_to()` one beat at a time.
The initial arrival is coupled to layer entry; later stages require the player's
actions, never an unpaired redraw or timer. Direct state construction belongs
to development seeds. Layer reset semantics belong to [world layers](world-layers-mechanic.md).
`reunion_complete()` means the stage has reached `complete`, including later stages.

## Evening tells

At `complete`, window, mug and Nika attention can reveal `FROST_WOOD_GRAIN`,
`KNUCKLES_BIRCH` and `DELAYED_SMILE`. The shared
[evening beats](../../game/story/evening.py) narrate them in that order, even
when fixtures are addressed out of order. The consent-door action supplies any
still unseen before moving to `consented`. Close attention is optional; the
scenes are not. Repeating attention recalls the completed beat.

Dinner lands before the hand-on-the-plate tell. Tins and room observations may
recall it only after `KNUCKLES_BIRCH`; early tins/window attention must neither
pretend dinner happened nor log a night seam. The window retains the remaining
evening light until the appropriate later stage. No extra dinner flag is needed.

The chest remains the preparation cue until using the mattress actually makes
the bed. Describing the room cannot stack the fire or lay the mattress. The
sauna proposal concerns tonight and does not depend on yesterday's optional
visit. `MEMORY_ALOUD` is logged by the bed beat itself, beginning the night-seam
set without another hidden command.

## Responses and movement

Before coffee, `out` is held by care and the chair. After consent it is held by
the night, then by the live dawn offer; after refusal it begins the walk.
Every unavailable or repeated interaction has an authored stage-appropriate
response. The model cannot paraphrase the copy or add effects to these beats;
[narration priority](narration-priority.md) owns that rule.

Room callbacks and loaded redraws remember arrival instead of replaying the
fall through the door. The [quest view](quest-mechanic.md) may restate the
current visible invitation but never display a stage, flag or seam count.
Nika remains Nika in the fiction until the knowing completes, as the bible
requires. The stopped room after refusal is a distinct state, not a replay of
arrival or the evening's warmth.

Implementation: [false-cabin handlers](../../game/actions/use_handlers/false_cabin.py),
[evening order](../../game/story/evening.py), [room and door handling](../../game/map.py).
Use the [playtesting guide](../architecture/playtesting.md) for seeds and retained
routes; test out-of-order attention and restored stages as well as the main route.
