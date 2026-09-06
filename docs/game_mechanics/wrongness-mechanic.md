# Wrongness and tells

The log records which authored discrepancies Elli has observed, once each and
in insertion order. It survives save/load. It is never a player-facing counter,
clue list or journal headed Wrongness. If a future recall view is wanted, it
needs its own authored memory prose, not an exposed data structure.

## Identity and narration

Use `AnomalyID` and `log_tell(world_state, AnomalyID.X, player)`.
[anomalies.py](../../game/story/anomalies.py) owns stable identifiers and short
saved descriptions; [tells.py](../../game/story/tells.py) owns deduplication and
the fear step. Beat handlers own the player-facing discovery. Room rendering
may recall an observed tell, but must never log one or advance its beat.

Pass `player` from runtime code. The optional argument lets seeds and tests
construct state without a player; omitting it in production silently loses
the fear movement while leaving the gate satisfied. See [fear](fear-curve.md).
Acknowledgement is supported by the data model for later recall; current beats
generally log without acknowledging.

The legacy identifier `STONE_FORMATIONS` serialises as `stone_formations` but
now represents the missing deer path and emptied forest. It does not license
formations or engravings in the fiction. `CORRECTION_TURN` is retained only for
old saves. [Save/load](save-load-mechanic.md) owns migration commitments.

## Discovery and gate ownership

- The forest's fox tracks, hare and missing path land on arrival, with shared
  attention fallbacks for loaded positions in
  [morning.py](../../game/story/morning.py). Revisits recall the route without
  re-encountering the animals. The camera errand is separate; looking at tracks
  cannot repair it. [World layers](world-layers-mechanic.md#transition-contract)
  owns the specific encounter gate.
- [Reunion](reunion-mechanic.md#evening-tells) owns evening order, fixture triggers
  and consent completion of unseen tells.
- [Recognition](recognition-and-refusal.md#night-and-dawn) owns the night subset,
  required breathing seam, threshold, completion scene and shared dawn gate.

The general `WrongnessLog.threshold_met(n=3)` query is not interchangeable with
these story gates. An unrelated anomaly cannot replace a required forest tell
or night seam.

When adding an authorised tell, define its enum and saved description once,
call `log_tell()` from the narrated observation and update the relevant gate
only if intended. Verify deduplication, repeated attention and loaded positions
through that beat's existing tests or scenarios; do not duplicate every arc's
trigger table here.
