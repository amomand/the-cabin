"""Tests for authored cutscene playback."""

from game.cutscene import CUTSCENE_DISMISS_TEXT, Cutscene


def test_cutscene_play_uses_diegetic_dismiss_prompt(monkeypatch, capsys):
    cutscene = Cutscene("The light from the window seems dimmer now.")
    monkeypatch.setattr(cutscene, "_clear_terminal", lambda: None)
    monkeypatch.setattr(cutscene, "_wait_for_key", lambda: None)

    cutscene.play()

    output = capsys.readouterr().out
    assert CUTSCENE_DISMISS_TEXT in output
    assert "Press any key" not in output
    assert cutscene.has_played is True
