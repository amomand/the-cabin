"""Tests for WebGameSession — works without OpenAI API key via rule-based fallback."""

import pytest
from server.session import WebGameSession
from server.protocol import SessionPhase, RenderFrame
from game.ai_interpreter import clear_response_cache


@pytest.fixture(autouse=True)
def _clear_ai_cache():
    """Clear the AI interpreter response cache between tests to avoid cross-test pollution."""
    clear_response_cache()
    yield
    clear_response_cache()


class TestIntroPhase:
    def test_intro_frame_has_intro_text(self):
        session = WebGameSession()
        frame = session.get_intro_frame()
        assert "You shouldn't have come back." in frame.lines
        assert frame.wait_for_key is True
        assert frame.clear is True

    def test_starts_in_intro_phase(self):
        session = WebGameSession()
        assert session.phase == SessionPhase.INTRO_KEYPRESS

    def test_keypress_transitions_to_awaiting_input(self):
        session = WebGameSession()
        frame = session.handle_input("")  # keypress dismissal
        assert session.phase == SessionPhase.AWAITING_INPUT
        assert frame.prompt == "> "
        # Should contain room name
        assert any("Wilderness" in line for line in frame.lines)


class TestAwaitingInput:
    @pytest.fixture
    def session(self):
        s = WebGameSession()
        s.handle_input("")  # dismiss intro
        return s

    def test_look_command(self, session):
        frame = session.handle_input("look")
        assert session.phase == SessionPhase.AWAITING_INPUT
        assert frame.prompt == "> "
        # Should have health/fear line
        assert any("Health:" in line for line in frame.lines)

    def test_move_north(self, session):
        frame = session.handle_input("north")
        assert session.phase == SessionPhase.AWAITING_INPUT
        # Should now be in The Clearing
        assert any("Clearing" in line for line in frame.lines)

    def test_inventory_command(self, session):
        frame = session.handle_input("inventory")
        assert frame.prompt == "> "
        assert any("Health:" in line for line in frame.lines)

    def test_take_item(self, session):
        frame = session.handle_input("take stick")
        assert session.phase == SessionPhase.AWAITING_INPUT
        assert frame.prompt == "> "

    def test_empty_input(self, session):
        frame = session.handle_input("")
        assert session.phase == SessionPhase.AWAITING_INPUT
        assert frame.prompt == "> "

    def test_quit_ends_session(self, session):
        frame = session.handle_input("quit")
        assert session.phase == SessionPhase.ENDED
        assert frame.game_over is True

    def test_ended_session_returns_game_over(self, session):
        session.handle_input("quit")
        frame = session.handle_input("anything")
        assert frame.game_over is True


class TestSaveLoadDisabled:
    @pytest.fixture
    def session(self):
        s = WebGameSession()
        s.handle_input("")  # dismiss intro
        return s

    def test_save_returns_diegetic_message(self, session):
        frame = session.handle_input("save")
        assert session.phase == SessionPhase.AWAITING_INPUT
        assert any("wilderness" in line.lower() or "forward" in line.lower() for line in frame.lines)

    def test_load_returns_diegetic_message(self, session):
        frame = session.handle_input("load")
        assert session.phase == SessionPhase.AWAITING_INPUT
        assert any("wilderness" in line.lower() or "forward" in line.lower() for line in frame.lines)


class TestQuestOverlay:
    @pytest.fixture
    def session(self):
        s = WebGameSession()
        s.handle_input("")  # dismiss intro
        return s

    def test_quest_screen_shows_overlay(self, session):
        frame = session.handle_input("quest")
        assert session.phase == SessionPhase.OVERLAY_KEYPRESS
        assert frame.wait_for_key is True
        assert frame.clear is True

    def test_quest_overlay_dismissal_returns_to_room(self, session):
        session.handle_input("quest")
        frame = session.handle_input("")  # dismiss overlay
        assert session.phase == SessionPhase.AWAITING_INPUT
        assert frame.prompt == "> "

    def test_map_screen_shows_overlay(self, session):
        frame = session.handle_input("map")
        assert session.phase == SessionPhase.OVERLAY_KEYPRESS
        assert frame.wait_for_key is True


class TestRoomTransitions:
    @pytest.fixture
    def session(self):
        s = WebGameSession()
        s.handle_input("")  # dismiss intro
        return s

    def test_move_to_clearing_and_back(self, session):
        frame = session.handle_input("north")
        assert any("Clearing" in line for line in frame.lines)
        assert frame.clear is True

        frame = session.handle_input("south")
        assert any("Wilderness" in line for line in frame.lines)

    def test_invalid_direction_stays_in_room(self, session):
        frame = session.handle_input("east")
        assert session.phase == SessionPhase.AWAITING_INPUT
        # Should still be in Wilderness
        assert session.map.current_room.id == "wilderness_start"


class TestRenderFrame:
    def test_to_dict_minimal(self):
        frame = RenderFrame(lines=["Hello"])
        d = frame.to_dict()
        assert d == {"type": "render", "lines": ["Hello"]}

    def test_to_dict_full(self):
        frame = RenderFrame(
            lines=["Test"],
            clear=True,
            prompt="> ",
            wait_for_key=True,
            game_over=True,
        )
        d = frame.to_dict()
        assert d["type"] == "render"
        assert d["clear"] is True
        assert d["prompt"] == "> "
        assert d["wait_for_key"] is True
        assert d["game_over"] is True


class TestCutsceneIntegration:
    """Test that entering the cabin from clearing triggers a cutscene overlay."""

    def test_cabin_entry_cutscene(self):
        session = WebGameSession()
        session.handle_input("")  # dismiss intro

        # Move to clearing
        session.handle_input("north")
        assert session.map.current_room.id == "cabin_clearing"

        # Enter cabin — should trigger cutscene overlay
        frame = session.handle_input("cabin")

        # Either we get a cutscene overlay or the room render
        # (depends on whether cutscene file exists)
        if session.phase == SessionPhase.OVERLAY_KEYPRESS:
            assert frame.wait_for_key is True
            # Dismiss cutscene
            frame = session.handle_input("")
            assert session.phase == SessionPhase.AWAITING_INPUT
        # After cutscene, should be in cabin
        assert session.map.current_room.id == "cabin_main"
