"""Tests for WebGameSession — works without OpenAI API key via rule-based fallback."""

import pytest
from unittest.mock import patch
from server.session import WebGameSession
from server.protocol import RenderFrame, SessionPhase
from game.ai_interpreter import clear_response_cache
from game.cutscene import CUTSCENE_DISMISS_TEXT


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

    def test_exit_phrase_keeps_session_open(self, session):
        frame = session.handle_input("exit the cabin")
        assert session.phase == SessionPhase.AWAITING_INPUT
        assert frame.game_over is not True

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

    def test_move_north_from_clearing_enters_cabin(self, session):
        session.handle_input("north")

        frame = session.handle_input("north")

        assert session.map.current_room.id == "cabin_main"
        assert any("You step inside" in line for line in frame.lines)

    def test_invalid_direction_stays_in_room(self, session):
        frame = session.handle_input("east")
        assert session.phase == SessionPhase.AWAITING_INPUT
        # Should still be in Wilderness
        assert session.map.current_room.id == "wilderness_start"


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

        assert session.phase == SessionPhase.OVERLAY_KEYPRESS
        assert frame.wait_for_key is True
        assert f"*{CUTSCENE_DISMISS_TEXT}*" in frame.lines

        # Dismiss the cutscene. The cold room then opens Warm Up, so a second
        # overlay waits behind it: the scene sets up the room the quest reacts
        # to, and it must land in that order.
        quest_frame = session.handle_input("")

        assert session.phase == SessionPhase.OVERLAY_KEYPRESS
        assert any("The lights don't respond" in line for line in quest_frame.lines)

        # Dismiss the quest opening
        session.handle_input("")

        assert session.phase == SessionPhase.AWAITING_INPUT
        # After the overlays, should be in cabin
        assert session.map.current_room.id == "cabin_main"


class TestOverlaysQueuedOnTheClosingTurn:
    """A run that ends on the same turn as a scripted scene must still show it.

    The terminal prints cutscenes inline as the turn runs, so it always showed
    the scene. The web dropped its overlay queue on the closing frame, which
    deleted the Act II flight on one surface and not the other.
    """

    def _turn_that_queues_a_scene_and_ends_the_run(self, session):
        """Stand in for the turn where the flight is queued and fear hits 100."""
        def fake_turn(_text):
            session._pending_overlays.append(
                RenderFrame(
                    lines=[
                        "You run.",
                        "A tree full on.",
                        "",
                        f"*{CUTSCENE_DISMISS_TEXT}*",
                    ],
                    clear=True,
                    wait_for_key=True,
                )
            )
            session.phase = SessionPhase.ENDED
            return RenderFrame(
                lines=["You are consumed by its darkness."], game_over=True
            )
        return fake_turn

    def test_the_queued_scene_is_folded_into_the_closing_frame(self):
        session = WebGameSession()
        session.handle_input("")  # dismiss intro

        with patch.object(
            session, "_process_game_input",
            side_effect=self._turn_that_queues_a_scene_and_ends_the_run(session),
        ):
            frame = session.handle_input("east")

        assert "A tree full on." in frame.lines
        assert "You are consumed by its darkness." in frame.lines
        # In order: the scene, then the last word.
        assert frame.lines.index("A tree full on.") < frame.lines.index(
            "You are consumed by its darkness."
        )

    def test_the_session_stays_shut_with_no_keypress_owed(self):
        session = WebGameSession()
        session.handle_input("")  # dismiss intro

        with patch.object(
            session, "_process_game_input",
            side_effect=self._turn_that_queues_a_scene_and_ends_the_run(session),
        ):
            frame = session.handle_input("east")

        assert frame.wait_for_key is False
        # No key left to press, so nothing should ask for one.
        assert f"*{CUTSCENE_DISMISS_TEXT}*" not in frame.lines
        assert session._pending_overlays == []
        assert session.phase == SessionPhase.ENDED
        assert session.handle_input("").game_over is True


class TestBlankInputIsNotATurn:
    """A raced keypress or bare Enter must not run a game turn.

    The client sends a keypress message for every keydown while an overlay
    is up. A double-tap or key auto-repeat can land a second keypress after
    the overlay is already dismissed; it arrives as blank text and used to
    run a full turn — empty input to the interpreter, plus a second
    Health/Fear status line appended to the transcript.
    """

    @pytest.fixture
    def session(self):
        s = WebGameSession()
        s.handle_input("")  # dismiss intro
        return s

    def test_blank_input_renders_nothing(self, session):
        frame = session.handle_input("   ")
        assert frame.lines == []
        assert frame.prompt == "> "
        assert session.phase == SessionPhase.AWAITING_INPUT

    def test_blank_input_never_reaches_interpreter(self, session, monkeypatch):
        def _fail(*args, **kwargs):
            raise AssertionError("interpret() must not run for blank input")

        monkeypatch.setattr("game.turn.interpret", _fail)
        session.handle_input("")
        session.handle_input("   ")

    def test_raced_keypress_after_cutscene_does_not_repeat_status(self, session):
        session.handle_input("north")
        # Cabin entry queues two overlays: the entry cutscene, then the Warm Up
        # opening the cold room triggers.
        session.handle_input("cabin")
        assert session.phase == SessionPhase.OVERLAY_KEYPRESS

        session.handle_input("")  # keypress dismisses the cutscene
        assert session.phase == SessionPhase.OVERLAY_KEYPRESS

        room_frame = session.handle_input("")  # and the quest opening
        assert any(line.startswith("Health:") for line in room_frame.lines)

        # A second keypress raced in before the client saw the room frame.
        raced = session.handle_input("")
        assert raced.lines == []


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


class TestTerminalParity:
    """Pins behaviour that must match GameEngine (pre-#113 drift fixes)."""

    @pytest.fixture
    def session(self, tmp_path):
        s = WebGameSession()
        s.handle_input("")  # dismiss intro
        s.save_manager = s.save_manager.__class__(save_dir=tmp_path / "saves")
        return s

    def test_fire_lit_event_reduces_fear(self, session):
        from game.actions.base import ActionResult

        session.player.fear = 30
        result = ActionResult(
            success=True,
            feedback="",
            events=["fire_lit"],
            state_changes={"fire_lit": True, "fear_reduction": 5},
        )

        session._handle_action_events(result, intent=None)

        assert session.player.fear == 25

    def test_load_into_death_state_ends_run(self, session):
        from game.death import DEATH_LINE_FEAR_COLLAPSE

        session.player.fear = 100  # save at the fear-collapse threshold
        session.handle_input("save doom")
        session.player.fear = 0

        frame = session.handle_input("load doom")

        assert session.phase == SessionPhase.ENDED
        assert frame.game_over is True
        assert DEATH_LINE_FEAR_COLLAPSE in frame.lines

    def test_load_into_finished_story_ends_run(self, session):
        from game.ending import END_LINE_STAYED

        session.map.world_state.ending = "stayed"  # save after the stayed ending
        session.handle_input("save stayed")
        session.map.world_state.ending = "none"

        frame = session.handle_input("load stayed")

        assert session.phase == SessionPhase.ENDED
        assert frame.game_over is True
        assert END_LINE_STAYED in frame.lines

    def test_load_into_legacy_ending_stays_closed(self, session):
        session.map.world_state.ending = "refused"
        session.handle_input("save old-ending")
        session.map.world_state.ending = "none"

        frame = session.handle_input("load old-ending")

        assert session.map.world_state.ending == "refused"
        assert session.phase == SessionPhase.ENDED
        assert frame.game_over is True

    def test_escape_stays_open_until_the_coda_finishes(self, session):
        session.map.world_state.ending = "escaped"
        session.map.world_state.coda_stage = "home"

        assert session._ending_frame_if_over() is None
        assert session.phase == SessionPhase.AWAITING_INPUT

    def test_escape_closes_on_the_final_coda_line(self, session):
        from game.ending import END_LINE_ESCAPED

        session.map.world_state.ending = "escaped"
        session.map.world_state.coda_stage = "end"

        frame = session._ending_frame_if_over()

        assert frame is not None
        assert session.phase == SessionPhase.ENDED
        assert frame.game_over is True
        assert END_LINE_ESCAPED in frame.lines
