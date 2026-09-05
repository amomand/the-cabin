# The evening, sleep and first morning

The bed requires the voicemail and saved frames. Power, cabin fire and sauna
use are independent optional chores. Their eight combinations all reach both
endings in `tests/test_turn_parity.py` through real commands on both surfaces.

The missing mug is established by `story/arrival.py:reopen_cabin`, called from
successful evening fire-lighting, the first voicemail, the real mug, or the meal.
It narrates buckets, bedding appropriate to the heat, the empty hook and cupboard,
and the white mug once, setting `reopening_done`. It never depends on Warm Up
completion. A no-fire, no-power route therefore retains the later mug memory.

`use table` narrates the meal and sets `evening_meal`. If it has not happened,
the bed action narrates it before sleep. With fire she heats soup; without it she
eats bread and butter. Both routes leave the corked bottle and empty glass on the
counter. A repeated meal or sleep never repeats dinner.

`use bed` sets `first_morning` and records `slept_cold = not fire_lit`.
A cold night costs 10 health (`COLD_NIGHT_HEALTH`) once, with interrupted sleep,
stiff fingers and no log restoring sound. A warm night retains the log's sound.
Both wake at ten past eight with the window still black. Power and sauna have no
health charge. Reusing the bed does not sleep again or charge health again.

Leaving the bedroom for the main room narrates breakfast and the grey daylight,
setting `morning_started` in the shared movement result. Coffee is prepared over
an existing fire; without one the kettle stays cold. Description callbacks never
advance this beat. Later fire-lighting changes `fire_lit`, not `slept_cold`.

These history flags are explicit persisted booleans. Legacy saves infer the old
meal/morning from `first_morning` and the old reopening from a completed first night or power plus fire;
missing `slept_cold` defaults false, without retroactive damage. The coda reads
whether a real fire was ever lit, including one lit after a cold night.

`first_morning` enables the grounds' fox-track arrival. The separate camera
errand then moves through testing, new battery and image comparison. Both
forest entrances wait for the comparison; the woods deliver the hare and
missing path on arrival. The evening lake walk is open, with the climb into
the forest refused until the errand. See `act-two-authoring.md`.
