"""Tests for protocol types."""

from server.protocol import RenderFrame


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

        assert frame.to_dict() == {"type": "render", "lines": ["test"]}

    def test_to_dict_includes_true_flags(self):
        frame = RenderFrame(
            lines=["x"],
            clear=True,
            prompt="> ",
            wait_for_key=True,
            game_over=True,
        )

        assert frame.to_dict() == {
            "type": "render",
            "lines": ["x"],
            "clear": True,
            "prompt": "> ",
            "wait_for_key": True,
            "game_over": True,
        }
