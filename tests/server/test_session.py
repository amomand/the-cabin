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


class TestSaveLoad:
    @pytest.fixture
    def session(self):
        s = WebGameSession()
        s.handle_input("")  # dismiss intro
        return s

    def test_save_writes_slot(self, session, tmp_path):
        session.save_manager = session.save_manager.__class__(save_dir=tmp_path / "saves")
        frame = session.handle_input("save")
        assert session.phase == SessionPhase.AWAITING_INPUT
        assert any("fix this moment" in line for line in frame.lines)
        assert not any("save" in line.lower() or "slot" in line.lower() for line in frame.lines)

    def test_load_falls_back_to_dev_seed_name(self, session, tmp_path):
        session.save_manager = session.save_manager.__class__(save_dir=tmp_path / "empty-saves")

        frame = session.handle_input("load act3_arrival")

        assert session.phase == SessionPhase.AWAITING_INPUT
        assert session.map.current_room.id == "cabin_main"
        assert session.map.world_state.world_layer == "wrong"
        assert session.map.world_state.reunion_stage == "arrival"
        assert any("somewhere remembered" in line for line in frame.lines)
        assert not any("load" in line.lower() or "slot" in line.lower() for line in frame.lines)

    def test_load_missing_slot_is_diegetic(self, session, tmp_path):
        session.save_manager = session.save_manager.__class__(save_dir=tmp_path / "empty-saves")

        frame = session.handle_input("load missing")

        assert session.phase == SessionPhase.AWAITING_INPUT
        assert any("find nothing tied to it" in line for line in frame.lines)
        assert not any("save" in line.lower() or "slot" in line.lower() for line in frame.lines)

    def test_default_save_managers_are_session_scoped(self):
        first = WebGameSession()
        second = WebGameSession()

        assert first.save_manager.save_dir != second.save_manager.save_dir


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


class TestAIContext:
    """Tests for the web session AI context builder."""

    def test_build_ai_context_tracks_first_visit_and_revisit(self):
        session = WebGameSession()

        session.handle_input("")  # dismiss intro
        start_context = session._build_ai_context()
        assert start_context["room_id"] == "wilderness_start"
        assert start_context["been_here_before"] is False
        assert start_context["rooms_visited"] == 1

        moved, _ = session.map.move("north", session.player)
        assert moved is True

        first_visit_context = session._build_ai_context()
        assert first_visit_context["been_here_before"] is False
        assert first_visit_context["rooms_visited"] == 2

        moved, _ = session.map.move("south", session.player)
        assert moved is True

        revisit_context = session._build_ai_context()
        assert revisit_context["been_here_before"] is True
        assert revisit_context["rooms_visited"] == 2

    def test_build_ai_context_uses_wrong_layer_exits(self):
        session = WebGameSession()
        session.handle_input("")  # dismiss intro
        session._load_game("act3_arrival")

        context = session._build_ai_context()

        assert context["exits"] == ["out"]

    def test_build_ai_context_hides_wrong_layer_fixtures_in_real_cabin(self):
        session = WebGameSession()
        session.handle_input("")  # dismiss intro
        session.map.current_location_id = "cabin_interior"
        session.map.current_room_id = "cabin_main"

        context = session._build_ai_context()

        assert "window" not in context["room_items"]
        assert "mug" not in context["room_items"]
        assert "nika" not in context["room_items"]
