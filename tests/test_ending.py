"""Unit tests for the shared ending decision and closing lines."""

from game.ending import (
    END_LINE_ESCAPED,
    END_LINE_STAYED,
    ending_line_for,
    ending_reached,
)
from game.world_state import WorldState


def _world(ending: str, coda_stage: str = "none") -> WorldState:
    ws = WorldState()
    ws.ending = ending
    ws.coda_stage = coda_stage
    return ws


def test_no_ending_leaves_the_run_open():
    assert ending_reached(WorldState()) is False
    assert ending_reached(_world("none")) is False


def test_legacy_endings_close_the_run():
    assert ending_reached(_world("accepted")) is True
    assert ending_reached(_world("refused")) is True
    assert ending_line_for(_world("accepted")) is None
    assert ending_line_for(_world("refused")) is None


def test_stayed_ending_closes_at_once():
    assert ending_reached(_world("stayed")) is True
    assert ending_line_for(_world("stayed")) == END_LINE_STAYED


def test_escape_stays_open_until_the_coda_ends():
    assert ending_reached(_world("escaped")) is False
    assert ending_line_for(_world("escaped")) is None
    assert ending_reached(_world("escaped", "scraping")) is False

    finished = _world("escaped", "end")
    assert ending_reached(finished) is True
    assert ending_line_for(finished) == END_LINE_ESCAPED


def test_missing_or_empty_ending_is_treated_as_open():
    class Bare:
        pass

    assert ending_reached(Bare()) is False
    assert ending_reached(_world("")) is False
