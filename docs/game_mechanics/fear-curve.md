# The Fear Curve

How `player.fear` moves across a run, and where each step is defined.

## Three channels

| Channel | Where | Size |
|---|---|---|
| AI-returned effects | `game/turn.py::apply_effects` | clamped to ±2 a turn |
| Event-driven | `game/turn.py::handle_action_events` | `fire_lit` −5, `thrown_into_darkness` +5 |
| **Authored beats** | `game/story/fear.py` | the table below |

The ±2 clamp is right for improvised action and useless for a scripted scene. The scripted beats therefore move fear on their own terms, and every step lives in `game/story/fear.py` so the curve can be read, argued with, and tuned in one place.

This channel exists because the back half of the game had no fear movement at all. The Act II climax was the only beat past Act I that touched the stat, and every rule-based intent carries `effects=None`, so the AI channel contributed nothing either. Acts III–V are played almost entirely through `use`, `wait`, `look`, `move`, `accept` and `refuse`, all of which resolve rule-based. The meter sat at 40 for twenty-five turns of the most frightening material in the story (#185).

## Two rules the table follows

**Motivated, not monotonic.** The lie is comfort. Being tended, sat down and handed coffee *lowers* fear, because that is the trap working. The tells, the door onto no drive, and the knowing raise it. A curve that only climbed would say the reunion is frightening, and the reunion is the opposite of frightening, which is the horror of it.

**Scripted beats do not kill.** `fear.shift()` clamps at `AUTHORED_CEILING` (99), one short of the collapse threshold in `game/death.py`. The Act II climax already worked this way. A run ends on the dawn choice or on the player's own exhaustion, never mid-scene because a beat happened to land on 100. Note the consequence: fear-collapse death is unreachable from authored beats alone in Acts III–V. That is deliberate — the endings are the endings.

## The steps

| Beat | Constant | Step | Where it fires |
|---|---|---|---|
| The Act II flight | `CLIMAX_FLIGHT` | +40 | `Map._trigger_lyer_encounter` |
| Any newly observed tell | `TELL_OBSERVED` | +4 | `game/story/tells.py::log_tell` |
| Nika crosses and tends her | `REUNION_TENDED` | −8 | `UseAction`, `nika` at `arrival` |
| The chair and the verdict | `REUNION_SEATED` | −5 | `UseAction`, `nika` at `tended` |
| The first mouthful | `REUNION_COMPLETE` | −6 | `UseAction`, `mug` at `seated` |
| The door onto no drive | `CONSENT_DOOR` | +10 | `Map.move`, the consent beat |
| Bedding down | `BEDDED` | −8 | `UseAction`, `mattress` at `consented` |
| The knowing | `RECOGNITION` | +15 | `game/story/night.py::maybe_finish_the_knowing` |
| Taking the mug at dawn | `DAWN_STAYED` | −35 | `AcceptAction` |
| Refusing it | `DAWN_ESCAPED` | +10 | `RefuseAction` |
| Crossing the threshold | `WALKOUT_THRESHOLD` | +5 | `Map.move` |
| The woods | `WALKOUT_WOODS` | +5 | `Map.move` |
| Coming home | `ARRIVE_HOME` | −20 | `Map._arrive_home` |
| Making the call | `CODA_CALLED` | +5 | `UseAction`, `phone` at `home` |
| The scraping under the boards | `CODA_SCRAPING` | +10 | `WaitAction` at `called` |

`BEDDED` is sized to outweigh the `MEMORY_ALOUD` tell the same beat logs, so bedding down reads as settling rather than as nothing happening.

## Threading the player through

`log_tell()` and `maybe_finish_the_knowing()` both take an optional `player`. It is optional so dev seeds and tests can build wrongness state without one; passed, the beat also costs her something. A missing player means the beat still fires and only the stat move is skipped.

Tells are deduped by the wrongness log, so seeing the same wrongness twice moves nothing. The fear is in noticing, not in looking again.

## Dev seeds

The Act III+ seeds in `game/devtools/seed_saves.py` used to flip the layer by hand with `enter_wrong_layer()`, which skipped the climax entirely and produced saves at fear 0 and full health — not a state play can reach. `seed_act3_arrival` now routes through the real `Map._trigger_lyer_encounter`, and the later seeds apply their own beats' steps from the same constants, so the seeds stay in step with the curve by construction.

## Where the curve lands

The committed golden-path scenario is the reference run. Roughly: 12 at the Act II threshold, 52 straight after the flight, down to 33 across the reunion, 70 when the knowing lands, 90 at the far end of the walk out, and 85 at the scraping. The stayed ending closes around 35, though you cannot read that off `act5_accept_route.txt` — it ends on the ending line with no trailing status, so the last visible reading there is the pre-choice 70. Read `reports/playtests/act1_to_act5_golden_path.txt` for the current numbers rather than trusting this paragraph.

Act I still has no authored fear movement — the only step available to it is the `fire_lit` −5, which floors at 0. That is out of scope here (#185 is about the back half) but it does mean the gauge reads 0 until the first tell.

## Known rough edges

The walk-out steps fire on the transition, not once per run, so looping `cabin_main ↔ cabin_clearing` during the escape re-narrates the threshold beat and re-applies its +5. The prose repetition is pre-existing; the fear repetition is new. It is bounded by `AUTHORED_CEILING` and cannot kill, but a player who paces the doorway will watch the number climb.

## Tests

`tests/test_fear_curve.py` pins movement and direction, not totals. A test that hard-coded the numbers would only be the table written twice; the point is that each beat moves fear, and in the right direction.
