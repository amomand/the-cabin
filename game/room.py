from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Dict, List, Optional, Tuple

from game.requirements import Requirement
from game.item import Item

if TYPE_CHECKING:
    from game.world_state import WorldState


# Fallback denials for a direction the room does not offer. The world resists
# through what the player can feel, so these are sensory, not spatial
# instructions — and the indoor one exists because a wall is not a treeline.
DENIAL_OUTDOORS = "You turn that way and stop. Just trees and dark."
DENIAL_INDOORS = "You turn that way and stop. Wall, and the cold behind it."


# A description callback: (player, world_state, base_text, revisit) -> str.
# `revisit` is True when the player has been in this room before, or is
# looking again from inside it, so a description can narrate an act (finding
# the key, hearing the car cool) once and describe what is there after.
DescriptionFn = Callable[[object, "WorldState", str, bool], str]


class Room:
    """A room within a location.

    - `exits` map direction string to a tuple of `(target_location_id, target_room_id)`.
      This is room-level routing and may cross location boundaries.
    - `exit_criteria` are checked before leaving this room via any exit.
    - `get_description` can procedurally compose text from player, world state
      and whether this is a revisit.
    """

    def __init__(
        self,
        name: str,
        description: str,
        *,
        room_id: Optional[str] = None,
        exit_criteria: Optional[List[Requirement]] = None,
        description_fn: Optional[DescriptionFn] = None,
        items: Optional[List[Item]] = None,
        is_indoors: bool = False,
        wrong_name: Optional[str] = None,
        wrong_description: Optional[str] = None,
        wrong_description_fn: Optional[DescriptionFn] = None,
        wrong_exits: Optional[Dict[str, Tuple[str, str]]] = None,
        denial_text: Optional[str] = None,
        wrong_denial_text: Optional[str] = None,
    ) -> None:
        self.id = room_id or name.lower().replace(" ", "_")
        self.name = name
        # The name the player sees in the wrong layer, when the wrong layer's
        # version of the room is not the same place (the walk out crosses
        # woods that are not the track she walked in on).
        self.wrong_name: Optional[str] = wrong_name
        self.static_description = description
        # exits: direction -> (location_id, room_id)
        self.exits: Dict[str, Tuple[str, str]] = {}
        self.exit_criteria = exit_criteria or []
        # Optional override: function(player, world_state, base_text) -> str
        self._description_fn = description_fn
        # Items in this room
        self.items: List[Item] = items or []
        self.is_indoors = is_indoors

        # Wrong-layer overlays. When world_state.is_wrong_layer() is True and
        # an overlay is present, it is used in place of the real-layer version.
        # The cabin IS the cabin until it isn't.
        self.wrong_description: Optional[str] = wrong_description
        self._wrong_description_fn = wrong_description_fn
        self.wrong_exits: Dict[str, Tuple[str, str]] = wrong_exits or {}

        # Authored refusals for directions this room does not offer. Left
        # unset, the room falls back to the indoor or outdoor default.
        self.denial_text: Optional[str] = denial_text
        self.wrong_denial_text: Optional[str] = wrong_denial_text

    # Backward-compat convenience
    @property
    def description(self) -> str:  # type: ignore[override]
        return self.static_description

    @description.setter
    def description(self, value: str) -> None:
        self.static_description = value

    def _is_wrong_layer(self, world_state: WorldState) -> bool:
        try:
            return bool(getattr(world_state, "is_wrong_layer", lambda: False)())
        except Exception:
            return False

    def _has_wrong_overlay(self) -> bool:
        return self.wrong_description is not None or self._wrong_description_fn is not None

    def display_name(self, world_state: Optional[WorldState] = None) -> str:
        """Return the name the player sees for this room in the current layer."""
        if (
            world_state is not None
            and self.wrong_name is not None
            and self._is_wrong_layer(world_state)
        ):
            return self.wrong_name
        return self.name

    def get_description(
        self,
        player,  # noqa: ANN001
        world_state: WorldState,
        revisit: bool = False,
    ) -> str:
        """Compose the room description for the current world layer.

        `revisit` says whether the player has been here before, or is looking
        again from inside the room. Callers that render on arrival pass the
        map's own record; a `look` from inside the room is always a revisit,
        because the arrival has already shown the room once.
        """
        layer_is_wrong = self._is_wrong_layer(world_state)

        if layer_is_wrong and self._has_wrong_overlay():
            base = self.wrong_description if self.wrong_description is not None else self.static_description
            if self._wrong_description_fn is not None:
                base = self._wrong_description_fn(player, world_state, base, revisit)
            return base

        base = self.static_description
        if self._description_fn is not None:
            base = self._description_fn(player, world_state, base, revisit)

        # Items are appended by LookAction rather than baked into every room
        # description.
        return base

    def effective_exits(self, world_state: WorldState) -> Dict[str, Tuple[str, str]]:
        """Return the exits that apply in the current world layer.

        If wrong_exits is set and the world is in the wrong layer, those are
        used in place of the real-layer exits. Otherwise the normal exits apply.
        """
        if self._is_wrong_layer(world_state) and self.wrong_exits:
            return self.wrong_exits
        return self.exits

    def movement_denial(self, world_state: WorldState) -> str:
        """Return the refusal for a direction this room does not offer.

        Resolves in the same order as `get_description`: a wrong-layer
        override wins, then the room's own authored line, then the default
        for where the player is standing. `is_indoors` is what keeps the
        wilderness line out of interiors, including rooms nobody has written
        a denial for yet.
        """
        if self._is_wrong_layer(world_state) and self.wrong_denial_text is not None:
            return self.wrong_denial_text
        if self.denial_text is not None:
            return self.denial_text
        return DENIAL_INDOORS if self.is_indoors else DENIAL_OUTDOORS

    def get_items_description(self, world_state: Optional[WorldState] = None) -> str:
        """Get a description of items in this room for when the player looks around.

        In the wrong layer, rooms with authored overlay prose own the whole scene:
        the generic object-label list is suppressed so authored prose stays the
        single source of truth. Items with an empty room_description (wrong-layer
        fixtures) are never listed.
        """
        if world_state is not None and self._is_wrong_layer(world_state) and self._has_wrong_overlay():
            return ""

        item_descriptions = [item.room_description for item in self.items if item.room_description]
        if not item_descriptions:
            return ""
        return " " + " ".join(item_descriptions)
    
    def add_item(self, item: Item) -> None:
        """Add an item to this room."""
        self.items.append(item)
    
    def remove_item(self, item_name: str) -> Optional[Item]:
        """Remove an item from this room by name. Returns the item if found."""
        # Clean the item name - remove articles and normalize
        clean_name = self._clean_item_name(item_name)
        for i, item in enumerate(self.items):
            if item.name.lower() == clean_name:
                return self.items.pop(i)
        return None
    
    def get_item(self, item_name: str) -> Optional[Item]:
        """Get an item from this room by name without removing it."""
        clean_name = self._clean_item_name(item_name)
        for item in self.items:
            if item.name.lower() == clean_name:
                return item
        return None
    
    def has_item(self, item_name: str) -> bool:
        """Check if this room has an item with the given name."""
        clean_name = self._clean_item_name(item_name)
        return any(item.name.lower() == clean_name for item in self.items)
    
    def _clean_item_name(self, item_name: str) -> str:
        """Clean item name by removing articles and normalizing."""
        # Remove common articles
        articles = {"a", "an", "the"}
        words = item_name.lower().split()
        words = [word for word in words if word not in articles]
        return " ".join(words)

    def on_enter(self, player, world_state: WorldState) -> None:  # noqa: ANN001
        # Hook for one-time triggers or ambient effects
        return
