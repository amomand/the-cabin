# The five frames

The five frames are saved on Elli's phone, known by heart, and rewatched at the
main-room window after the voicemail. `use camera feed` and subsequent
`use phone` calls use the same authored handler. `footage_reviewed` records the
first rewatch, which changes fear by `CAMERA_FOOTAGE` once. The bed requires it.

The konttori has a separate `monitor` fixture with no story beat. Its screen and
router are dark without mains power. With power there are three live feeds and
a black northern feed until the camera is repaired; afterwards all four are live.
Looking or using the monitor never marks the saved frames reviewed.

In the current Phase 2 implementation, the fox-track attention beat still
contains the camera repair; its logged tell is also the repair evidence used by
the monitor description. The battery camera connects directly to the phone over
its local signal, so this does not require the cabin router or cellular reception.
Phase 3 will separate the errand into narrated stages and give completion its own
state. The bible's re-routed forest remains a target until that phase.

Code: `actions/use_handlers/act_one.py`, `map.py:observe_current_room`,
`story/real_rooms.py:konttori`, `ai_context.py`. The repair-return scenario checks
both powered monitor output and persistence after the repair.
