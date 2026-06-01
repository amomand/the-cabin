"""Unit tests for the shared death-line decision (game.death.death_line_for)."""

from game.death import (
    DEATH_LINE_FADE,
    DEATH_LINE_FEAR_COLLAPSE,
    death_line_for,
)
from game.player import Player


def _player(*, health: int = 100, fear: int = 0) -> Player:
    player = Player()
    player.health = health
    player.fear = fear
    return player


def test_alive_returns_none():
    assert death_line_for(_player(health=100, fear=0)) is None


def test_health_at_zero_returns_fade_line():
    assert DEATH_LINE_FADE == "At last, you are still enough to keep."
    assert death_line_for(_player(health=0, fear=0)) == DEATH_LINE_FADE


def test_fear_at_hundred_returns_collapse_line():
    assert DEATH_LINE_FEAR_COLLAPSE == "You are consumed by its darkness."
    assert death_line_for(_player(health=100, fear=100)) == DEATH_LINE_FEAR_COLLAPSE


def test_fear_collapse_takes_precedence_when_both_cross():
    # The mind goes before the body when both thresholds land the same turn.
    assert death_line_for(_player(health=0, fear=100)) == DEATH_LINE_FEAR_COLLAPSE
