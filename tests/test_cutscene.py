"""Tests for authored cutscene playback."""

from hashlib import sha256

import pytest

import game.cutscene as cutscene_module
from game.cutscene import (
    AUTHORED_CUTSCENE_RULE,
    CUTSCENE_DISMISS_TEXT,
    Cutscene,
    CutsceneManager,
)


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


def _authored_asset(body: str) -> str:
    return f"{AUTHORED_CUTSCENE_RULE}\n\n{body}\n\n{AUTHORED_CUTSCENE_RULE}\n"


def _write_other_authored_asset(directory, missing_name: str) -> None:
    other_name = (
        "lyer-encounter" if missing_name == "entering-cabin" else "entering-cabin"
    )
    (directory / f"{other_name}.txt").write_text(
        _authored_asset("The other scene remains intact."),
        encoding="utf-8",
    )


@pytest.mark.parametrize("missing_name", ["entering-cabin", "lyer-encounter"])
def test_declared_authored_assets_are_required(monkeypatch, tmp_path, missing_name):
    _write_other_authored_asset(tmp_path, missing_name)
    monkeypatch.setattr(cutscene_module, "CUTSCENE_DIRECTORY", tmp_path)

    with pytest.raises(FileNotFoundError, match=missing_name):
        CutsceneManager()


@pytest.mark.parametrize(
    ("invalid_text", "message"),
    [
        ("", "missing its required framing"),
        ("The flight without its frame.\n", "missing its required framing"),
        (
            _authored_asset("   "),
            "has no story text",
        ),
    ],
)
def test_declared_authored_assets_reject_empty_or_malformed_text(
    monkeypatch,
    tmp_path,
    invalid_text,
    message,
):
    (tmp_path / "entering-cabin.txt").write_text(invalid_text, encoding="utf-8")
    (tmp_path / "lyer-encounter.txt").write_text(
        _authored_asset("The other scene remains intact."),
        encoding="utf-8",
    )
    monkeypatch.setattr(cutscene_module, "CUTSCENE_DIRECTORY", tmp_path)

    with pytest.raises(ValueError, match=message):
        CutsceneManager()


def test_declared_authored_assets_propagate_decode_failures(monkeypatch, tmp_path):
    (tmp_path / "entering-cabin.txt").write_bytes(b"\xff")
    (tmp_path / "lyer-encounter.txt").write_text(
        _authored_asset("The other scene remains intact."),
        encoding="utf-8",
    )
    monkeypatch.setattr(cutscene_module, "CUTSCENE_DIRECTORY", tmp_path)

    with pytest.raises(UnicodeDecodeError):
        CutsceneManager()


def test_declared_authored_assets_propagate_read_failures(monkeypatch):
    def unreadable(path, *, encoding):
        raise PermissionError(path)

    monkeypatch.setattr(cutscene_module.Path, "read_text", unreadable)

    with pytest.raises(PermissionError):
        CutsceneManager()


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
