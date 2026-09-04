# Act I authoring decisions (#264, Phase 2)

The work follows the game-side bible. The normal evening keeps its practical
reopening, brief sauna warmth, evidence and sleep. Optional chores change physical
experience without removing knowledge required by the false cabin.

| Beat | Trigger | Recorded fact | Repeat / later dependency |
| --- | --- | --- | --- |
| Reopening | First evening fire, first voicemail at window, real mug or meal | `reopening_done`; buckets, bedding, empty hook, cupboard search and white mug narrated together | One implementation; later uses describe the white mug. False-cabin coffee and the night seam can remember the discovery on every route. |
| Voicemail | Phone/window in real main room | `voicemail_heard` | Next use reopens frames. The refusal can quote the warning. No heat prerequisite. |
| Frames | Phone after voicemail, or explicit camera-feed use at that window | `footage_reviewed` | Callback only; the morning comparison has its earlier image. |
| Meal | Table, or bed before first sleep if unfinished | `evening_meal` | Soup if fire exists, bread and butter otherwise. Corked bottle and glass persist into morning and coda. |
| Sleep | Bed after voicemail and frames | `first_morning`, `slept_cold` | Cold costs 10 health once. Bed cannot repeat sleep. Later heat does not change the night. |
| Grey morning | First move from bedroom to main room after sleep | `morning_started` | Breakfast, coffee only with a fire, daylight and northward look; returning never repeats them. |

Physical adaptation: the battery camera offers a direct local phone connection.
The router and monitor use mains power; the repaired northern feed becomes visible
on the monitor when power exists. This resolves the no-power route without changing
reception at the window. The combined fox/repair action remains until Phase 3.

The phone is equipment, not a takeable room object. The interpreter's `equipment`
list permits use without permitting model-proposed inventory additions. Window
and real mug interactions are now visible in real-cabin context. The real bedroom holds the bed; the false-cabin night keeps its authored
bed-and-mattress arrangement.

Required downstream repairs included here: true power/fire descriptions in the
coda; phone in the worn jacket during the walk out; coda exterior closure; monitor
after repair; cold sauna in the morning. The false cabin remains lit by its own
fire and lamp; its wall controls cannot change real power. Old disk slots migrate
phone/frame placements to the new equipment and fixtures. No conditional claim of "first warmth" is introduced.

The deeper-forest layout, staged camera errand and its completion gate remain
Phase 3. The evening shoreline is already ordinary and the deeper woods refuse
until morning. Wrong-layer structure, encounter prose and endings are unchanged.

A shared-turn priority repair was necessary: quest event callbacks could replace
the new reopening prose after it set its flag. A non-empty authored result now
wins after the callbacks, while the empty encounter movement still delegates to
its cutscene. The eight-evening, two-ending parity test checks that the discovery
actually reaches the player exactly once, not merely that its flag was set.

Verification includes all eight combinations through both endings, ordinary
full-story transcripts, the saved cold/dark route, the cold-night/later-fire repair
return, and the existing overlay/load/parity suite. Tests that required fire or
sauna before sleep, or frames in the konttori, have been replaced by the new
behavioural contract. Source manuscript snapshots are unchanged.
