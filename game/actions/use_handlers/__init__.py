"""Cohesive item-use handlers behind the registry-facing UseAction facade."""

from __future__ import annotations

from typing import Callable

from game.actions.base import ActionContext, ActionResult
from game.actions.use_handlers.act_one import use_bed, use_camera_feed, use_sauna_stove, use_table, use_monitor
from game.actions.use_handlers.false_cabin import (
    use_mattress,
    use_mug,
    use_nika,
    use_tins,
    use_window,
)
from game.actions.use_handlers.generic import use_generic
from game.actions.use_handlers.phone import use_phone
from game.actions.use_handlers.utilities import (
    use_circuit_breaker,
    use_fireplace,
    use_light_switch,
    use_matches,
)
from game.item import Item

ItemUseHandler = Callable[[ActionContext, Item], ActionResult]

ITEM_USE_HANDLERS: dict[str, ItemUseHandler] = {
    "phone": use_phone,
    "table": use_table,
    "monitor": use_monitor,
    "camera feed": use_camera_feed,
    "sauna stove": use_sauna_stove,
    "bed": use_bed,
    "circuit breaker": use_circuit_breaker,
    "matches": use_matches,
    "light switch": use_light_switch,
    "fireplace": use_fireplace,
    "window": use_window,
    "mug": use_mug,
    "nika": use_nika,
    "mattress": use_mattress,
    "tins": use_tins,
}

__all__ = ["ITEM_USE_HANDLERS", "ItemUseHandler", "use_generic"]
