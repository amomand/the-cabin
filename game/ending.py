"""Shared ending-state logic for terminal and web surfaces.

An Act V ending is terminal by design. The authored closing narration is the
story's last word, so the run stops when one fires — the engine holds still
rather than rendering another room. The decision lives here so `GameEngine`
and `WebGameSession` cannot drift apart, exactly as `game.death` does for
death. The render path stays per-surface; only the decision is shared.
"""


def ending_reached(world_state) -> bool:  # noqa: ANN001
    """True once an Act V ending has fired.

    Any value other than "none" counts, so the rewritten endings ("escaped",
    "stayed") close the run on the same terms as the legacy accept/refuse
    pair without this needing to know which arc is live.
    """
    return str(getattr(world_state, "ending", "none") or "none") != "none"
