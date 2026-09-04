# The voicemail at the window

The phone is carried story equipment from arrival, outside movable inventory.
The shared interpreter context exposes `equipment` separately from room items
and inventory; deterministic and model-assisted use resolve the same targets.
Taking or dropping equipment cannot remove the phone from the story.

In the real cabin, `use phone` or `use window` plays the voicemail at the
main-room window. Outside that room Elli leaves it until the window. Neither
power nor fire is a prerequisite. Before its first playback, the shared reopening
beat supplies any missing mug discovery. The voicemail sets `voicemail_heard`
and shifts fear by `VOICEMAIL_WARNING` once.

The next phone/window use opens the saved frames; later uses rewatch them without
replaying the voicemail or its fear change. `use camera feed` is also available,
but waits for the voicemail and the real cabin window. Sleep requires both.

In the false cabin the phone's night seam remains unchanged. After refusal,
Elli feels it through her worn jacket pocket. In the real coda the call still
belongs to the window and advances `coda_stage`; it is not another voicemail.

Code: `actions/use_handlers/phone.py`, `act_one.py`, `story/arrival.py`, and
`ai_context.py`. The phone's first-use and location gates are exercised through
normal commands in the cold/dark full-story scenario and focused action tests.
