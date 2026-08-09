"""Surface-agnostic save-slot commands shared by the terminal and web surfaces.

Save, load, list, and delete all decide the same two things regardless of
surface: what happens to the slot on disk, and what the player is told about
it. Both live here. What a surface does *afterwards* stays its own business,
which is why `load_game` reports whether state actually changed rather than
performing any re-render itself.

Companion to `game.turn`, and the same principle: shared decision, per-surface
render path.
"""

from __future__ import annotations

from dataclasses import dataclass

from game.game_state import GameState


SAVE_FIXED = "You fix this moment in your mind. The room holds still around it."
SAVES_NONE = "You reach back through your memory and find no fixed points."
SAVES_HEADING = "Moments you have fixed:"
SLOT_MISSING = "You reach for that thread and find nothing tied to it."
LOAD_SETTLED = "For a moment the room slips. When it settles, you are somewhere remembered."


def _slot_released(slot_name: str) -> str:
    return f"You let go of {slot_name}. The thread frays and falls away."


@dataclass(frozen=True)
class LoadOutcome:
    """The result of a load attempt.

    ``loaded`` is False when the slot held nothing, in which case no game state
    was touched and the surface should not run its post-load resets.
    """

    feedback: str
    loaded: bool


def save_game(
    save_manager,
    slot_name: str,
    *,
    player,
    game_map,
    quest_manager,
    cutscene_manager,
) -> str:
    """Write the current state to a slot and return the player-facing line."""
    state = GameState(
        player=player,
        map=game_map,
        quest_manager=quest_manager,
        cutscene_manager=cutscene_manager,
    )
    save_manager.save_game(state, slot_name)
    return SAVE_FIXED


def list_saves(save_manager) -> str:
    """Return the player-facing listing of every slot on disk."""
    saves = save_manager.list_saves()
    if not saves:
        return SAVES_NONE

    lines = [SAVES_HEADING]
    for info in saves:
        lines.append(f"  {info.slot_name}")
    return "\n".join(lines)


def delete_save(save_manager, slot_name: str) -> str:
    """Delete a slot if it exists and return the player-facing line."""
    if save_manager.delete_save(slot_name):
        return _slot_released(slot_name)
    return SLOT_MISSING


def load_game(
    save_manager,
    slot_name: str,
    *,
    player,
    game_map,
    quest_manager,
    cutscene_manager,
) -> LoadOutcome:
    """Load a slot into the given state, falling back to permanent dev seeds.

    Game state is only touched when a slot (or seed) actually resolves, so a
    miss leaves the run exactly as it was.
    """
    save_data = save_manager.load_game(slot_name)

    if save_data is None:
        try:
            from game.devtools import seed_saves
        except ImportError:
            seed_saves = None

        if seed_saves is not None and slot_name in seed_saves.SEEDS:
            save_data = seed_saves.SEEDS[slot_name]().to_dict()

    if save_data is None:
        return LoadOutcome(feedback=SLOT_MISSING, loaded=False)

    GameState.from_dict(
        save_data,
        player,
        game_map,
        quest_manager,
        cutscene_manager,
    )
    return LoadOutcome(feedback=LOAD_SETTLED, loaded=True)
