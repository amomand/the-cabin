"""Shared death-state logic for terminal and web surfaces.

The closing lines and precedence rule live here so both `GameEngine` and
`WebGameSession` end the run on the same terms. The render path stays
per-surface — only the decision is shared.
"""

from typing import Optional


DEATH_LINE_FEAR_COLLAPSE = "The dark consumes you."
DEATH_LINE_FADE = "The dark watches you fade."


def death_line_for(player) -> Optional[str]:
    """Return the closing line for a dead player, or None if still alive.

    Fear collapse is checked first: when both thresholds land in the same
    turn, the mind goes before the body.
    """
    if player.fear >= 100:
        return DEATH_LINE_FEAR_COLLAPSE
    if player.health <= 0:
        return DEATH_LINE_FADE
    return None
