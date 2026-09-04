# The sauna evening

The sauna is optional. First use of its stove narrates taking a towel, feeding
wood for half an hour, and sitting through the heat. `sauna_used` records that
visit. It has no health effect and is not a sleep gate.

The stove is wood-fired; the low electric lights depend on `has_power`. This
preserves the lights in the source story without making heating depend on the
breaker. A repeat that evening acknowledges the stones' remaining heat. After
`first_morning`, the room and stove both describe cold stones; Elli keeps her
coat on and leaves the sauna for the camera errand.

Skipping the sauna does not imply that the cabin was unheated. Likewise, using
it does not prevent a cold night in an unheated bedroom. False-cabin firelight
and the lamp do not depend on either choice. A line proposing a sauna tonight
does not need changing merely because Elli skipped it yesterday.

Code: `actions/use_handlers/act_one.py:use_sauna_stove`,
`story/real_rooms.py:sauna`. All eight evening combinations are exercised through
both endings in the parity tests.
