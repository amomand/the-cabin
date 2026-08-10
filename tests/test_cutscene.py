"""Tests for authored cutscene playback."""

from hashlib import sha256

import pytest

from game.cutscene import CUTSCENE_DISMISS_TEXT, Cutscene, CutsceneManager


EXPECTED_AUTHORED_TEXT_DIGESTS = {
    "entering-cabin": "4b627384b7e9ee11e07eefe384dd29d2b115bb74c5b7f725acd259cfbd4878f8",
    "lyer-encounter": "7b8b0f785c0fdca6d41ee5813db84102ee3abe5525c7bc7803164a73982b472b",
}


def test_cutscene_play_uses_diegetic_dismiss_prompt(monkeypatch, capsys):
    cutscene = Cutscene("The light from the window seems dimmer now.")
    monkeypatch.setattr(cutscene, "_clear_terminal", lambda: None)
    monkeypatch.setattr(cutscene, "_wait_for_key", lambda: None)

    cutscene.play()

    output = capsys.readouterr().out
    assert CUTSCENE_DISMISS_TEXT in output
    assert "Press any key" not in output
    assert cutscene.has_played is True


def test_runtime_asset_move_preserves_authored_text_byte_for_byte():
    manager = CutsceneManager()

    actual = {
        cutscene.cutscene_id: sha256(cutscene.text.encode("utf-8")).hexdigest()
        for cutscene in manager.cutscenes
    }

    assert actual == EXPECTED_AUTHORED_TEXT_DIGESTS


@pytest.mark.parametrize(
    ("from_room_id", "to_room_id", "expected_cutscene_id"),
    [
        ("cabin_clearing", "cabin_main", "entering-cabin"),
        ("old_woods", "cabin_main", "lyer-encounter"),
    ],
)
def test_runtime_asset_move_preserves_authored_triggers(
    from_room_id,
    to_room_id,
    expected_cutscene_id,
):
    manager = CutsceneManager()

    matching_ids = [
        cutscene.cutscene_id
        for cutscene in manager.cutscenes
        if cutscene.should_trigger(
            from_room_id=from_room_id,
            to_room_id=to_room_id,
        )
    ]

    assert matching_ids == [expected_cutscene_id]
