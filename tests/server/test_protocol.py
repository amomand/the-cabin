"""Tests for protocol types."""

from server.protocol import RenderFrame, SessionPhase


class TestSessionPhase:
    def test_all_phases_exist(self):
        assert SessionPhase.INTRO_KEYPRESS
        assert SessionPhase.AWAITING_INPUT
        assert SessionPhase.OVERLAY_KEYPRESS
        assert SessionPhase.ENDED


class TestRenderFrame:
    def test_defaults(self):
        frame = RenderFrame()
        assert frame.lines == []
        assert frame.clear is False
        assert frame.prompt is None
        assert frame.wait_for_key is False
        assert frame.game_over is False

    def test_to_dict_omits_false_flags(self):
        frame = RenderFrame(lines=["test"])
        d = frame.to_dict()
        assert "clear" not in d
        assert "prompt" not in d
        assert "wait_for_key" not in d
        assert "game_over" not in d

    def test_to_dict_includes_true_flags(self):
        frame = RenderFrame(lines=["x"], clear=True, prompt="> ", wait_for_key=True, game_over=True)
        d = frame.to_dict()
        assert d["clear"] is True
        assert d["prompt"] == "> "
        assert d["wait_for_key"] is True
        assert d["game_over"] is True
