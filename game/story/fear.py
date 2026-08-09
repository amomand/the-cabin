"""Authored fear movement for the scripted beats.

AI-returned effects are clamped to +/-2 a turn in `game/turn.py`, which is right
for improvised action and useless for a scripted scene. The beats below move
fear on their own terms, and every step lives in this one table so the curve can
be read, argued with, and tuned in one place.

Two rules the table follows:

**Motivated, not monotonic.** The lie is comfort. Being tended, sat down and
given coffee lowers fear, because that is the trap working; the tells and the
knowing raise it. A curve that only climbs would say the reunion is frightening,
and the reunion is the opposite of frightening, which is the horror of it.

**Scripted beats do not kill.** Authored shifts clamp at `AUTHORED_CEILING`,
one short of the collapse threshold in `game/death.py`. The Act II climax
already worked this way. A run ends on the dawn choice or on the player's own
exhaustion, never mid-scene because a scripted beat happened to land on 100.
"""

from __future__ import annotations

MIN_FEAR = 0

# One short of the `fear >= 100` collapse in `game/death.py`.
AUTHORED_CEILING = 99


# --- Act I: evidence before the first tell --------------------------------

# The shape on the feed is more than an isolated tell, but still only an
# image: distant, silent, and contained by the screen.
CAMERA_FOOTAGE = 5

# Nika knows the cabin and tells Elli not to go. Hearing fear in her oldest
# friend's voice lands harder than the footage.
VOICEMAIL_WARNING = 7

# --- Act II ---------------------------------------------------------------

# The run, the tree, the ground sideways. The single largest step in the game.
CLIMAX_FLIGHT = 40

# --- Anomalies ------------------------------------------------------------

# Every newly observed tell, wherever it is seen. Small, because the weight is
# in the accumulation: eight of these is most of a whole beat.
TELL_OBSERVED = 4

# --- Act III: the reunion, which is the lie working ------------------------

# She crosses the room, grips your arm, and the care lands.
REUNION_TENDED = -8
# A chair, the heat, the ordinary shape of sitting down with someone.
REUNION_SEATED = -5
# The first mouthful, made exactly how you take it.
REUNION_COMPLETE = -6

# The door opens onto no drive, no car, and a treeline that is not the
# treeline. The lie goes spatial, and it is the largest single tell.
CONSENT_DOOR = 10

# She chooses the warm room, and the arrangement assembles itself out of forty
# summers of habit. The choosing is hers, which is what settles her. Sized to
# outweigh the tell the same beat logs, so bedding down reads as settling
# rather than as nothing happening.
BEDDED = -8

# --- Act IV: the knowing ---------------------------------------------------

# The authored recognition at the night-seam threshold.
RECOGNITION = 15

# --- Act V: the dawn choice and after --------------------------------------

# Taking the mug is surrender, and the fear goes quiet with her.
DAWN_STAYED = -35
# Refusing it stops the pretence, and what is left does not pretend.
DAWN_ESCAPED = 10

# The walk out. Neither step is an attack; both are the woods being finished
# with her, which is worse.
WALKOUT_THRESHOLD = 5
WALKOUT_WOODS = 5

# Real frost, real light, her own boot prints from the morning before.
ARRIVE_HOME = -20

# --- The coda --------------------------------------------------------------

CODA_CALLED = 5
# Under the boards, in the real cabin.
CODA_SCRAPING = 10


def shift(player, delta: int) -> None:
    """Apply an authored fear step, bounded and safe to call with no player.

    `player` is optional because several beat helpers are reachable from dev
    tooling and tests that carry world state but no player. A missing player
    means the beat still fires; only the stat move is skipped.
    """
    if player is None or not delta:
        return

    current = getattr(player, "fear", 0) or 0
    player.fear = max(MIN_FEAR, min(AUTHORED_CEILING, current + delta))
