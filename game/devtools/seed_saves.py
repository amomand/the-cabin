"""
Dev tool: generate named save files at known story beats for playtesting.

Saves are written to `saves/dev/<name>.json`. Use `--use <name>` to copy a
seed into the main `saves/` directory so it can be loaded from inside the
game with `load <name>`.

Not for player use. Imports the story flags directly, so this only makes
sense on branches that have the corresponding story content.

Usage:
    python -m game.devtools.seed_saves           # regenerate all seeds
    python -m game.devtools.seed_saves list      # show available seeds
    python -m game.devtools.seed_saves use NAME  # copy seed into saves/ for loading
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path
from typing import Callable, Dict

from game.cutscene import CutsceneManager
from game.game_state import GameState
from game.map import Map
from game.persistence import SaveManager
from game.player import Player
from game.quest import QuestStatus
from game.quests import create_quest_manager
from game.story import ANOMALY_DESCRIPTIONS, AnomalyID, fear, log_tell


DEV_SAVE_DIR = Path("saves/dev")
MAIN_SAVE_DIR = Path("saves")


def _fresh() -> GameState:
    return GameState(
        player=Player(),
        map=Map(),
        quest_manager=create_quest_manager(),
        cutscene_manager=CutsceneManager(),
    )


def _goto(state: GameState, room_id: str, been_here_before: bool = True) -> None:
    state.map.visited_rooms.add(room_id)
    state.map._set_current_room_by_id(room_id, been_here_before=been_here_before)


def _mark_cutscene_played(state: GameState, cutscene_id: str) -> None:
    """Mark an authored cutscene as already played on a seed.

    Seeds stand for states the player has already walked through, so the
    cutscenes those states passed must not still be armed. Without this,
    loading an Act V seed and stepping back into the wrong cabin played the
    Act I entry scene — the pack set down, the karjalanpiirakka memory —
    immediately before "The pretence has stopped."
    """
    for cutscene in state.cutscene_manager.cutscenes:
        if cutscene.cutscene_id == cutscene_id:
            cutscene.has_played = True
            return
    raise KeyError(f"no cutscene with id {cutscene_id!r}")


def _complete_warm_up(state: GameState) -> None:
    state.quest_manager.completed_quests = ["warm_up"]
    state.quest_manager.active_quest = None
    state.quest_manager.quests["warm_up"].status = QuestStatus.COMPLETED


def seed_act1_end() -> GameState:
    """Just woken after sauna and bedroom sleep, before coming through to breakfast."""
    state = _fresh()
    ws = state.world_state
    ws.has_power = True
    ws.fire_lit = True
    ws.voicemail_heard = True
    ws.footage_reviewed = True
    ws.sauna_used = True
    ws.first_morning = True
    ws.reopening_done = True
    ws.evening_meal = True
    ws.morning_started = False
    fear.shift(state.player, fear.CAMERA_FOOTAGE + fear.VOICEMAIL_WARNING)
    _complete_warm_up(state)
    _mark_cutscene_played(state, "entering-cabin")
    for room in ("wilderness_start", "cabin_clearing", "cabin_main", "konttori",
                 "cabin_grounds_main", "sauna", "lakeside", "bedroom"):
        state.map.visited_rooms.add(room)
    _goto(state, "bedroom")
    return state


def seed_act2_mid() -> GameState:
    """At Dead Pines: camera compared, fox and hare observed, missing path ahead."""
    state = seed_act1_end()
    ws = state.world_state
    ws.morning_started = True
    ws.camera_stage = "compared"
    log_tell(ws, AnomalyID.FOX_TRACKS, state.player)
    log_tell(ws, AnomalyID.HARE, state.player)
    state.map.visited_rooms.update({"wood_track"})
    _goto(state, "deer_path")
    return state


def seed_act3_arrival() -> GameState:
    """Just fell through the wrong cabin door. Nika on her feet, reunion not begun.

    Routes through the real climax rather than flipping the layer by hand, so
    the seed carries the fear and the cracked ribs the flight actually costs.
    Setting `enter_wrong_layer()` directly produced an Act III save at fear 0
    and full health, which is not a state play can reach (#185).
    """
    state = seed_act2_mid()
    ws = state.world_state
    log_tell(ws, AnomalyID.STONE_FORMATIONS, state.player)
    _goto(state, "old_woods")
    state.map._trigger_lyer_encounter(state.player)
    _mark_cutscene_played(state, "lyer-encounter")
    return state


def seed_act3_seated() -> GameState:
    """Settled into a chair in the wrong cabin. Coffee in front of her, not yet tasted."""
    state = seed_act3_arrival()
    state.world_state.reunion_stage = "seated"
    fear.shift(state.player, fear.REUNION_TENDED + fear.REUNION_SEATED)
    return state


def seed_act3_consented() -> GameState:
    """The consent-door beat has fired. She chose the warm room; night ahead."""
    state = seed_act3_seated()
    ws = state.world_state
    ws.reunion_stage = "consented"
    ws.consent_given = True
    fear.shift(state.player, fear.REUNION_COMPLETE + fear.CONSENT_DOOR)
    for anomaly in (
        AnomalyID.FROST_WOOD_GRAIN,
        AnomalyID.KNUCKLES_BIRCH,
        AnomalyID.DELAYED_SMILE,
    ):
        log_tell(ws, anomaly, state.player)
    return state


def seed_act4_night() -> GameState:
    """Bedded down in the dark beside the copy. Night seams ready to gather."""
    state = seed_act3_consented()
    ws = state.world_state
    ws.reunion_stage = "bedded"
    fear.shift(state.player, fear.BEDDED)
    log_tell(ws, AnomalyID.MEMORY_ALOUD, state.player)
    return state


def seed_act4_recognition() -> GameState:
    """The knowing has finished. Recognition set, night seams logged, pre-dawn."""
    state = seed_act4_night()
    ws = state.world_state
    ws.reunion_stage = "night"
    ws.recognition = True
    log_tell(ws, AnomalyID.BREATHING_TIDE, state.player)
    log_tell(ws, AnomalyID.PHONE_DARK, state.player)
    log_tell(ws, AnomalyID.MUG_IMPOSSIBLE, state.player)
    log_tell(ws, AnomalyID.WRONG_TINS, state.player)
    log_tell(ws, AnomalyID.BLACK_BOARDS, state.player)
    log_tell(ws, AnomalyID.NO_CALL, state.player)
    fear.shift(state.player, fear.RECOGNITION)
    return state


def seed_act5_dawn() -> GameState:
    """Wrong grey morning. The blue mug is offered; both endings are live."""
    state = seed_act4_recognition()
    state.world_state.reunion_stage = "dawn"
    return state


def seed_coda_home() -> GameState:
    """Escaped and walked out. Back in the real cabin, the call not yet made."""
    state = seed_act5_dawn()
    ws = state.world_state
    ws.ending = "escaped"
    ws.exit_wrong_layer()
    ws.coda_stage = "home"
    _goto(state, "cabin_main")
    fear.shift(
        state.player,
        fear.DAWN_ESCAPED
        + fear.WALKOUT_THRESHOLD
        + fear.WALKOUT_WOODS
        + fear.ARRIVE_HOME,
    )
    return state


def seed_near_death_health() -> GameState:
    """Health at 2 in the forest. Any narrated harm ends the run."""
    state = _fresh()
    state.player.health = 2
    state.player.fear = 20
    _goto(state, "wilderness_start")
    return state


def seed_near_death_fear() -> GameState:
    """Fear at 98 in the wrong layer. One AI or event step tips into collapse.

    Not one more *tell*: authored steps clamp at `fear.AUTHORED_CEILING`, so a
    scripted beat can no longer end the run. Only the AI channel and the
    event-driven bumps can cross 100 from here.
    """
    state = seed_act3_arrival()
    state.player.fear = 98
    return state


def seed_death_health() -> GameState:
    """Real woods with health already at the terminal threshold."""
    state = _fresh()
    state.player.health = 0
    state.player.fear = 20
    return state


def seed_death_fear() -> GameState:
    """Real woods with fear already at the terminal threshold."""
    state = _fresh()
    state.player.fear = 100
    return state


SEEDS: Dict[str, Callable[[], GameState]] = {
    "act1_end": seed_act1_end,
    "act2_mid": seed_act2_mid,
    "act3_arrival": seed_act3_arrival,
    "act3_seated": seed_act3_seated,
    "act3_consented": seed_act3_consented,
    "act4_night": seed_act4_night,
    "act4_recognition": seed_act4_recognition,
    "act5_dawn": seed_act5_dawn,
    "coda_home": seed_coda_home,
    "near_death_health": seed_near_death_health,
    "near_death_fear": seed_near_death_fear,
    "death_health": seed_death_health,
    "death_fear": seed_death_fear,
}


def generate_all(save_dir: Path = DEV_SAVE_DIR) -> list[Path]:
    manager = SaveManager(save_dir=save_dir)
    written = []
    for name, builder in SEEDS.items():
        path = manager.save_game(builder(), slot_name=name)
        written.append(path)
    return written


def use_seed(name: str) -> Path:
    """Copy a dev seed into the main saves/ dir so the game can load it."""
    if name not in SEEDS:
        raise KeyError(f"Unknown seed {name!r}. Known: {', '.join(SEEDS)}")
    src = DEV_SAVE_DIR / f"{name}.json"
    if not src.exists():
        # Regenerate on the fly if missing.
        generate_all()
    MAIN_SAVE_DIR.mkdir(parents=True, exist_ok=True)
    dst = MAIN_SAVE_DIR / f"{name}.json"
    shutil.copyfile(src, dst)
    return dst


def _cmd_list() -> None:
    for name, builder in SEEDS.items():
        doc = (builder.__doc__ or "").strip().split("\n")[0]
        print(f"  {name:<20} {doc}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate dev save files at known story beats.")
    sub = parser.add_subparsers(dest="cmd")
    sub.add_parser("list", help="List available seeds.")
    sub.add_parser("generate", help="(Re)generate all seeds into saves/dev/.")
    use = sub.add_parser("use", help="Copy a seed into saves/ so the game can load it.")
    use.add_argument("name")
    args = parser.parse_args(argv)

    if args.cmd == "list":
        _cmd_list()
        return 0
    if args.cmd == "use":
        dst = use_seed(args.name)
        print(f"Copied to {dst}. In-game: load {args.name}")
        return 0
    # Default: regenerate all.
    paths = generate_all()
    print(f"Wrote {len(paths)} seeds to {DEV_SAVE_DIR}/:")
    for p in paths:
        print(f"  {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
