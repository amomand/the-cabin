"""Unit tests for the shared ending decision (game.ending.ending_reached)."""

from game.ending import ending_reached
from game.world_state import WorldState


def _world(ending: str) -> WorldState:
    ws = WorldState()
    ws.ending = ending
    return ws


def test_no_ending_leaves_the_run_open():
    assert ending_reached(WorldState()) is False
    assert ending_reached(_world("none")) is False


def test_legacy_endings_close_the_run():
    assert ending_reached(_world("accepted")) is True
    assert ending_reached(_world("refused")) is True


def test_rewritten_endings_close_the_run():
    """The #141 arc swap must not need a change here to stay terminal."""
    assert ending_reached(_world("escaped")) is True
    assert ending_reached(_world("stayed")) is True


def test_missing_or_empty_ending_is_treated_as_open():
    class Bare:
        pass

    assert ending_reached(Bare()) is False
    assert ending_reached(_world("")) is False
