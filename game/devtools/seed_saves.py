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
from game.quests import create_quest_manager
from game.story import ANOMALY_DESCRIPTIONS, AnomalyID, log_tell


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


def _complete_warm_up(state: GameState) -> None:
    state.quest_manager.completed_quests = ["warm_up"]
    state.quest_manager.active_quest = None


def seed_act1_end() -> GameState:
    """Morning after sauna and bedroom sleep. Act I beats all fired, ready to walk north."""
    state = _fresh()
    ws = state.world_state
    ws.has_power = True
    ws.fire_lit = True
    ws.voicemail_heard = True
    ws.footage_reviewed = True
    ws.sauna_used = True
    ws.first_morning = True
    _complete_warm_up(state)
    for room in ("wilderness_start", "cabin_clearing", "cabin_main", "konttori",
                 "cabin_grounds_main", "sauna", "lakeside", "bedroom"):
        state.map.visited_rooms.add(room)
    _goto(state, "bedroom")
    return state


def seed_act2_mid() -> GameState:
    """Mid-walk north: two anomalies observed, threshold not yet met."""
    state = seed_act1_end()
    ws = state.world_state
    log_tell(ws, AnomalyID.FOX_TRACKS)
    log_tell(ws, AnomalyID.HARE)
    _goto(state, "wood_track")
    return state


def seed_act3_arrival() -> GameState:
    """Just fell through the wrong cabin door. Nika on her feet, reunion not begun."""
    state = seed_act2_mid()
    ws = state.world_state
    log_tell(ws, AnomalyID.STONE_FORMATIONS)
    ws.lyer_encountered = True
    ws.enter_wrong_layer()  # sets world_layer=wrong, reunion_stage=arrival
    _goto(state, "cabin_main")
    return state


def seed_act3_seated() -> GameState:
    """Settled into a chair in the wrong cabin. Coffee in front of her, not yet tasted."""
    state = seed_act3_arrival()
    state.world_state.reunion_stage = "seated"
    return state


def seed_act4_recognition() -> GameState:
    """Correction-turn has fired. Recognition unlocked, refusal available in Act V."""
    state = seed_act3_seated()
    ws = state.world_state
    ws.reunion_stage = "complete"
    ws.wrong_outside_seen = True
    ws.recognition = True
    log_tell(ws, AnomalyID.CORRECTION_TURN)
    _goto(state, "old_woods")
    return state


SEEDS: Dict[str, Callable[[], GameState]] = {
    "act1_end": seed_act1_end,
    "act2_mid": seed_act2_mid,
    "act3_arrival": seed_act3_arrival,
    "act3_seated": seed_act3_seated,
    "act4_recognition": seed_act4_recognition,
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
