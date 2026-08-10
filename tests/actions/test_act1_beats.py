"""Tests for the Act I beats: voicemail, camera footage, sauna, bedroom sleep.

These live in UseAction branches driven by world_state flags.
"""
from unittest.mock import MagicMock

import pytest

from game import turn
from game.actions import create_default_registry
from game.actions.base import ActionContext, ModelEffectsPolicy
from game.actions.use import UseAction
from game.ai_interpreter import Intent
from game.events import EventBus
from game.player import Player
from game.story import fear
from game.world_state import WorldState


@pytest.fixture
def action():
    return UseAction()


@pytest.fixture
def ctx():
    """A minimally real ActionContext-shaped object.

    Uses real state and player objects; mocks only the surrounding action shell.
    """
    c = MagicMock()
    c.world_state = WorldState()
    c.player = Player()
    c.intent.reply = None
    c.ai_reply = None
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
        assert "cold room comes first" in result.feedback
        assert ctx.world_state.voicemail_heard is False

    def test_after_fire_lit_plays_voicemail_once(self, action, ctx):
        ctx.world_state.fire_lit = True
        ctx.intent.args = {"item": "phone"}
        ctx.room.get_item.return_value = _fake_item("phone")
        result = action.execute(ctx)
        assert result.success is True
        assert result.requests == ()
        assert "It's... it's lying out there" in result.feedback
        assert "The pause before the last line" in result.feedback
        assert "Nika does not pause" in result.feedback
        assert ctx.world_state.voicemail_heard is True
        assert ctx.player.fear == fear.VOICEMAIL_WARNING

    def test_replay_does_not_reflip_flag(self, action, ctx):
        ctx.world_state.fire_lit = True
        ctx.world_state.voicemail_heard = True
        ctx.intent.args = {"item": "phone"}
        ctx.room.get_item.return_value = _fake_item("phone")
        result = action.execute(ctx)
        assert result.requests == ()
        assert ctx.player.fear == 0


# --- Camera feed ------------------------------------------------------------

class TestCameraFeed:
    def test_review_sets_flag(self, action, ctx):
        ctx.intent.args = {"item": "camera feed"}
        ctx.room.get_item.return_value = _fake_item("camera feed")
        result = action.execute(ctx)
        assert result.success is True
        assert result.requests == ()
        assert ctx.world_state.footage_reviewed is True
        assert "five frames" in result.feedback.lower()
        assert ctx.player.fear == fear.CAMERA_FOOTAGE

    def test_replay_does_not_reflip_flag(self, action, ctx):
        ctx.world_state.footage_reviewed = True
        ctx.intent.args = {"item": "camera feed"}
        ctx.room.get_item.return_value = _fake_item("camera feed")
        result = action.execute(ctx)
        assert result.requests == ()
        assert ctx.player.fear == 0


def test_camera_and_voicemail_each_move_fear_once(action):
    """The two Act I evidence beats should register before the first tell."""
    player = Player()
    game_map = MagicMock()
    game_map.world_state = WorldState()
    game_map.current_room.get_item.side_effect = _fake_item

    camera = ActionContext(
        player=player,
        map=game_map,
        intent=Intent(action="use", args={"item": "camera feed"}, confidence=1.0),
    )
    action.execute(camera)
    after_camera = player.fear

    game_map.world_state.fire_lit = True
    phone = ActionContext(
        player=player,
        map=game_map,
        intent=Intent(action="use", args={"item": "phone"}, confidence=1.0),
    )
    action.execute(phone)
    after_voicemail = player.fear

    assert after_camera == fear.CAMERA_FOOTAGE
    assert after_voicemail == fear.CAMERA_FOOTAGE + fear.VOICEMAIL_WARNING


@pytest.mark.parametrize(
    ("item_name", "fire_lit", "expected_fear"),
    [
        ("camera feed", False, fear.CAMERA_FOOTAGE),
        ("phone", True, fear.VOICEMAIL_WARNING),
    ],
)
def test_model_effects_do_not_stack_on_authored_evidence(
    monkeypatch, item_name, fire_lit, expected_fear
):
    player = Player()
    game_map = MagicMock()
    game_map.world_state = WorldState(fire_lit=fire_lit)
    game_map.current_room.get_item.side_effect = _fake_item
    intent = Intent(
        action="use",
        args={"item": item_name},
        confidence=1.0,
        effects={"fear": 2},
    )
    monkeypatch.setattr(turn, "build_ai_context", lambda *args: {})
    monkeypatch.setattr(turn, "interpret", lambda *args: intent)

    turn.take_turn(
        f"use {item_name}",
        player=player,
        game_map=game_map,
        quest_manager=MagicMock(),
        action_registry=create_default_registry(),
        event_bus=EventBus(),
        set_feedback=lambda feedback: None,
    )

    assert player.fear == expected_fear
    assert intent.effects == {"fear": 2}


# --- Sauna ------------------------------------------------------------------

class TestSauna:
    def test_first_use_sets_flag(self, action, ctx):
        ctx.intent.args = {"item": "sauna stove"}
        ctx.intent.effects = {"fear": 5}
        ctx.room.get_item.return_value = _fake_item("sauna stove")
        result = action.execute(ctx)
        assert result.success is True
        assert result.requests == ()
        assert result.model_effects is ModelEffectsPolicy.BLOCK
        assert ctx.intent.effects == {"fear": 5}
        assert ctx.world_state.sauna_used is True


# --- Bed / sleep ------------------------------------------------------------

class TestBed:
    def test_before_fire_lit_is_too_cold(self, action, ctx):
        ctx.intent.args = {"item": "bed"}
        ctx.room.get_item.return_value = _fake_item("bed")
        result = action.execute(ctx)
        assert result.requests == ()
        assert ctx.world_state.first_morning is False

    def test_fire_lit_but_unfinished_beats_defer(self, action, ctx):
        ctx.world_state.fire_lit = True
        ctx.intent.args = {"item": "bed"}
        ctx.room.get_item.return_value = _fake_item("bed")
        result = action.execute(ctx)
        assert result.requests == ()
        assert ctx.world_state.first_morning is False

    def test_sauna_is_part_of_the_evening_before_sleep(self, action, ctx):
        ctx.world_state.fire_lit = True
        ctx.world_state.voicemail_heard = True
        ctx.world_state.footage_reviewed = True
        ctx.intent.args = {"item": "bed"}
        ctx.room.get_item.return_value = _fake_item("bed")
        result = action.execute(ctx)
        assert result.requests == ()
        assert "sauna is still cold" in result.feedback
        assert ctx.world_state.first_morning is False

    def test_all_beats_satisfied_advances_to_first_morning(self, action, ctx):
        ctx.world_state.fire_lit = True
        ctx.world_state.voicemail_heard = True
        ctx.world_state.footage_reviewed = True
        ctx.world_state.sauna_used = True
        ctx.intent.args = {"item": "bed"}
        ctx.intent.effects = {"fear": 5}
        ctx.room.get_item.return_value = _fake_item("bed")
        result = action.execute(ctx)
        assert result.requests == ()
        assert result.model_effects is ModelEffectsPolicy.BLOCK
        assert ctx.intent.effects == {"fear": 5}
        assert ctx.world_state.first_morning is True

    def test_already_morning_does_not_replay(self, action, ctx):
        ctx.world_state.first_morning = True
        ctx.intent.args = {"item": "bed"}
        ctx.room.get_item.return_value = _fake_item("bed")
        result = action.execute(ctx)
        assert result.requests == ()
