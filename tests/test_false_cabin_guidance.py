"""The quest overlay reflects the live false-cabin objective (#246).

Through the reunion, the night, and the dawn offer, the thing the story is
waiting on is an authored beat rather than a registered quest. The overlay
used to fall back to "Nothing pulls at you just now" at exactly those points,
telling the player there was no objective while the room held her on one.
"""

import builtins

import pytest

from game.devtools.seed_saves import SEEDS
from game.game_engine import GameEngine
from game.quest import QuestManager
from game.story.guidance import false_cabin_objective
from server.session import WebGameSession

NO_PULL = "Nothing pulls at you just now"


def _overlay_for(seed_name: str) -> str:
    state = SEEDS[seed_name]()
    return state.quest_manager.get_active_quest_display(
        state.map.world_state, state.map.current_room_id
    )


@pytest.mark.parametrize(
    "seed_name, expected_word",
    [
        ("act3_arrival", "nika"),
        ("act3_seated", "mug"),
        ("act3_consented", "mattress"),
        ("act4_night", "listen"),
        ("act4_recognition", "grey"),
        ("act5_dawn", "mug"),
    ],
)
def test_quest_overlay_names_the_live_false_cabin_objective(seed_name, expected_word):
    text = _overlay_for(seed_name)

    assert NO_PULL not in text
    assert expected_word in text.lower()


def test_quest_overlay_never_names_the_lyer():
    for seed_name in ("act3_seated", "act3_consented", "act5_dawn"):
        text = _overlay_for(seed_name).lower()
        assert "lyer" not in text
        assert "copy" not in text


def test_false_cabin_guidance_stays_out_of_the_real_cabin():
    """The guidance is gated on the wrong layer, the false cabin, and an
    unresolved ending; the real cabin keeps the quest-only overlay."""
    state = SEEDS["act1_end"]()
    assert false_cabin_objective(state.map.world_state, "cabin_main") is None

    coda = SEEDS["coda_home"]()
    assert false_cabin_objective(coda.map.world_state, "cabin_main") is None

    dawn = SEEDS["act5_dawn"]()
    dawn.world_state.ending = "escaped"
    assert false_cabin_objective(dawn.world_state, "cabin_main") is None
    assert false_cabin_objective(SEEDS["act5_dawn"]().world_state, "cabin_clearing") is None


def test_quest_manager_without_world_state_keeps_the_quest_only_view():
    manager = QuestManager()
    assert NO_PULL in manager.get_active_quest_display()


@pytest.mark.parametrize("seed_name", ["act3_seated", "act3_consented", "act5_dawn"])
def test_both_surfaces_render_the_same_false_cabin_guidance(
    seed_name, monkeypatch, capsys
):
    """The overlay is decided once and rendered by both surfaces."""
    import game.game_engine as game_engine_module

    engine = GameEngine()
    monkeypatch.setattr(engine, "clear_terminal", lambda: None)
    monkeypatch.setattr(
        game_engine_module.termios,
        "tcgetattr",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(game_engine_module.termios.error()),
    )
    monkeypatch.setattr(builtins, "input", lambda _prompt="": "")
    engine._load_game(seed_name)
    engine._show_quest_screen()
    terminal_out = capsys.readouterr().out

    session = WebGameSession()
    session.handle_input("")
    session._load_game(seed_name)
    frame = session.handle_input("quest")
    web_out = "\n".join(frame.lines)

    expected = _overlay_for(seed_name)
    assert expected in terminal_out
    assert expected in web_out
    assert NO_PULL not in terminal_out
    assert NO_PULL not in web_out
