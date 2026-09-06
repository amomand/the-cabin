# The fear curve

Fear changes through three channels: bounded model suggestions, shared turn
requests, and authored beats. [Effects](../architecture/effects.md) owns the
first two. [game/story/fear.py](../../game/story/fear.py) defines every authored
step, its size and its rationale; keep tuning there rather than maintaining a
second numeric table in documentation.

The curve follows the scene. Care, the chair, coffee and bed lower fear because
the comfortable lie is working. Seams, the wrong outside and recognition raise
it. A curve that only climbs would make the reunion frightening before Elli
has reason to doubt it. `BEDDED` outweighs the spoken-memory tell in the same
beat so settling into bed still feels like settling.

Authored fear shifts clamp at `AUTHORED_CEILING` (99), below the collapse
threshold. They cannot end the run halfway through a scene. The forest
collision separately keeps health above zero; cold sleep has its own health
consequence in [the morning contract](first_morning_miniquest.md). The
[death contract](death-mechanic.md) owns thresholds and ending precedence.

One-shot evidence and deduplicated tells move fear only on discovery, not on
replay. Authored results block extra model effects. `log_tell()` and
`maybe_finish_the_knowing()` require a player at runtime for their stat changes;
their optional argument exists for tools constructing story state.

Seeds must represent reachable costs: `act1_end` lights the fire before the
evidence, while `seed_act3_arrival` runs the actual climax rather than manually
flipping the layer with full health and no fear. Later builders draw their
steps from the shared constants. Input order can change totals, especially
when a reduction meets zero or a rise reaches the ceiling. Read current
[playtest transcripts](../architecture/playtesting.md) for route totals instead
of treating one total as the contract.

[tests/test_fear_curve.py](../../tests/test_fear_curve.py) checks movement and
direction. It should not become the constant table written twice.
