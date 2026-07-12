"""Shared story-ending logic for terminal and web surfaces.

The closing lines and the completion rule live here so both `GameEngine`
and `WebGameSession` end the run on the same terms, mirroring `game/death.py`.
The ending prose itself is authored in the action that lands it; these are
only the final lines that close the run.
"""

from typing import Optional


END_LINE_STAYED = "You are home."
END_LINE_ESCAPED = "You wait."


def ending_line_for(world_state) -> Optional[str]:
    """Return the closing line for a finished story, or None if still going.

    The stayed ending closes the run at once. The escape closes it only at
    the end of the coda, when she has sat down and listened.
    """
    if world_state.ending == "stayed":
        return END_LINE_STAYED
    if world_state.ending == "escaped" and world_state.coda_stage == "end":
        return END_LINE_ESCAPED
    return None
