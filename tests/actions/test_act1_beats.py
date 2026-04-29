"""Tests for the Act I beats: voicemail, camera footage, sauna, bedroom sleep.

These live in UseAction branches driven by world_state flags.
"""
from unittest.mock import MagicMock

import pytest

from game.actions.use import UseAction
from game.world_state import WorldState


@pytest.fixture
def action():
    return UseAction()


@pytest.fixture
def ctx():
    """A minimally real ActionContext-shaped object.

    Uses a real WorldState so dict-style assignment works; mocks player/room/intent.
    """
    c = MagicMock()
    c.world_state = WorldState()
    c.intent.reply = None
    c.ai_reply = None
    # Default: item not in inventory, fall through to room lookup.
    c.player.get_item.return_value = None
    c.player._clean_item_name.side_effect = lambda s: s.lower().strip()
    return c


def _fake_item(name: str):
    item = MagicMock()
    item.name = name
    return item


# --- Phone / voicemail ------------------------------------------------------

class TestPhone:
    def test_before_fire_is_lit_elli_puts_it_off(self, action, ctx):
        ctx.intent.args = {"item": "phone"}
        ctx.room.get_item.return_value = _fake_item("phone")
        result = action.execute(ctx)
        assert result.success is True
        assert "Settle the cabin first" in result.feedback
        assert ctx.world_state.voicemail_heard is False

    def test_after_fire_lit_plays_voicemail_once(self, action, ctx):
        ctx.world_state.fire_lit = True
        ctx.intent.args = {"item": "phone"}
        ctx.room.get_item.return_value = _fake_item("phone")
        result = action.execute(ctx)
        assert result.success is True
        assert "voicemail_heard" in result.events
        assert "waiting" in result.feedback.lower()
        assert ctx.world_state.voicemail_heard is True

    def test_replay_does_not_reflip_flag(self, action, ctx):
        ctx.world_state.fire_lit = True
        ctx.world_state.voicemail_heard = True
        ctx.intent.args = {"item": "phone"}
        ctx.room.get_item.return_value = _fake_item("phone")
        result = action.execute(ctx)
        assert "use_phone_again" in result.events


# --- Camera feed ------------------------------------------------------------

class TestCameraFeed:
    def test_review_sets_flag(self, action, ctx):
        ctx.intent.args = {"item": "camera feed"}
        ctx.room.get_item.return_value = _fake_item("camera feed")
        result = action.execute(ctx)
        assert result.success is True
        assert "footage_reviewed" in result.events
        assert ctx.world_state.footage_reviewed is True
        assert "five frames" in result.feedback.lower()

    def test_replay_does_not_reflip_flag(self, action, ctx):
        ctx.world_state.footage_reviewed = True
        ctx.intent.args = {"item": "camera feed"}
        ctx.room.get_item.return_value = _fake_item("camera feed")
        result = action.execute(ctx)
        assert "use_footage_again" in result.events


# --- Sauna ------------------------------------------------------------------

class TestSauna:
    def test_first_use_sets_flag(self, action, ctx):
        ctx.intent.args = {"item": "sauna stove"}
        ctx.room.get_item.return_value = _fake_item("sauna stove")
        result = action.execute(ctx)
        assert result.success is True
        assert "sauna_used" in result.events
        assert ctx.world_state.sauna_used is True


# --- Bed / sleep ------------------------------------------------------------

class TestBed:
    def test_before_fire_lit_is_too_cold(self, action, ctx):
        ctx.intent.args = {"item": "bed"}
        ctx.room.get_item.return_value = _fake_item("bed")
        result = action.execute(ctx)
        assert "use_bed_too_cold" in result.events
        assert ctx.world_state.first_morning is False

    def test_fire_lit_but_unfinished_beats_defer(self, action, ctx):
        ctx.world_state.fire_lit = True
        ctx.intent.args = {"item": "bed"}
        ctx.room.get_item.return_value = _fake_item("bed")
        result = action.execute(ctx)
        assert "use_bed_unfinished" in result.events
        assert ctx.world_state.first_morning is False

    def test_all_beats_satisfied_advances_to_first_morning(self, action, ctx):
        ctx.world_state.fire_lit = True
        ctx.world_state.voicemail_heard = True
        ctx.world_state.footage_reviewed = True
        ctx.intent.args = {"item": "bed"}
        ctx.room.get_item.return_value = _fake_item("bed")
        result = action.execute(ctx)
        assert "first_morning" in result.events
        assert ctx.world_state.first_morning is True

    def test_already_morning_does_not_replay(self, action, ctx):
        ctx.world_state.first_morning = True
        ctx.intent.args = {"item": "bed"}
        ctx.room.get_item.return_value = _fake_item("bed")
        result = action.execute(ctx)
        assert "use_bed_again" in result.events
