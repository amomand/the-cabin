# The five frames

The five frames are saved on Elli's phone, known by heart, and rewatched at the
main-room window after the voicemail. `use camera feed` and subsequent
`use phone` calls use the same authored handler. `footage_reviewed` records the
first rewatch, which changes fear by `CAMERA_FOOTAGE` once. The bed requires it.

The konttori has a separate `monitor` fixture with no story beat. Its screen and
router are dark without mains power. With power there are three live feeds and
a black northern feed until the camera is repaired; afterwards all four are live.
Looking or using the monitor never marks the saved frames reviewed.

The morning repair is a separate interaction with the `northern camera` fixture
at the grounds. `use camera` (also `test camera`, `replace battery`, or
`compare images`) advances one narrated stage at a time: testing the full but
ineffective battery, replacing it, then comparing the live feed against frame
one. `camera_stage` persists each step. `powered` restores the fourth monitor
feed; `compared` opens both forest approaches. Looking never repairs anything. At the grounds after replacement, `use phone`
or `use camera feed` makes the same comparison; it does not ask for cellular
reception while she is looking at the camera's local picture. Requests for
frames/pictures remain image requests: before repair they explain that a live
picture is still missing and cannot start testing or replace the battery.

The battery camera connects directly to the phone over its local signal, so
neither repair nor comparison needs the cabin router or cellular reception.
The fox tracks are a separate arrival tell. In an older slot that lacks the new
field, that formerly combined tell is evidence that the repair and comparison
already happened; no other tell or room position supplies that evidence.

Code: `story/morning.py`, `story/real_rooms.py:konttori`, `world_state.py`,
`map.py:real_route_denial`. The camera-stages scenario checks both gates, the
monitor before and after repair, intermediate saves and the final encounter.
