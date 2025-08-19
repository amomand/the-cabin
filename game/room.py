from __future__ import annotations

from typing import Callable, Dict, List, Optional, Tuple

from game.requirements import Requirement
from game.item import Item
from game.wildlife import Wildlife


class Room:
    """A room within a location.

    - `exits` map direction string to a tuple of `(target_location_id, target_room_id)`.
      This is room-level routing and may cross location boundaries.
    - `exit_criteria` are checked before leaving this room via any exit.
    - `get_description` can procedurally compose text from player and world state.
    """

    def __init__(
        self,
        name: str,
        description: str,
        *,
        room_id: Optional[str] = None,
        exit_criteria: Optional[List[Requirement]] = None,
        description_fn: Optional[Callable[[object, dict, str], str]] = None,
        items: Optional[List[Item]] = None,
        wildlife: Optional[List[Wildlife]] = None,
        max_wildlife: int = 2,
        wildlife_pool: Optional[Dict[str, Wildlife]] = None,
    ) -> None:
        self.id = room_id or name.lower().replace(" ", "_")
        self.name = name
        self.static_description = description
        # exits: direction -> (location_id, room_id)
        self.exits: Dict[str, Tuple[str, str]] = {}
        self.exit_criteria = exit_criteria or []
        # Optional override: function(player, world_state, base_text) -> str
        self._description_fn = description_fn
        # Items in this room
        self.items: List[Item] = items or []
        # Wildlife in this room
        self.wildlife: List[Wildlife] = wildlife or []
        self.max_wildlife = max_wildlife
        self.wildlife_pool = wildlife_pool or {}

    # Backward-compat convenience
    @property
    def description(self) -> str:  # type: ignore[override]
        return self.static_description

    @description.setter
    def description(self, value: str) -> None:
        self.static_description = value

    def get_description(self, player, world_state: dict) -> str:  # noqa: ANN001
        base = self.static_description
        if self._description_fn is not None:
            base = self._description_fn(player, world_state, base)
        
        # Items are no longer automatically included in room descriptions
        # They will be added by the AI interpreter when the player looks around
        return base
    
    def get_items_description(self) -> str:
        """Get a description of items in this room for when the player looks around."""
        if not self.items:
            return ""
        
        item_descriptions = [item.room_description for item in self.items]
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
    
    def get_wildlife(self, wildlife_name: str) -> Optional[Wildlife]:
        """Get wildlife from this room by name without removing it."""
        clean_name = self._clean_wildlife_name(wildlife_name)
        for animal in self.wildlife:
            if animal.name.lower() == clean_name:
                return animal
        return None
    
    def has_wildlife(self, wildlife_name: str) -> bool:
        """Check if this room has wildlife with the given name."""
        clean_name = self._clean_wildlife_name(wildlife_name)
        return any(animal.name.lower() == clean_name for animal in self.wildlife)
    
    def remove_wildlife(self, wildlife_name: str) -> Optional[Wildlife]:
        """Remove wildlife from this room by name. Returns the wildlife if found."""
        clean_name = self._clean_wildlife_name(wildlife_name)
        for i, animal in enumerate(self.wildlife):
            if animal.name.lower() == clean_name:
                return self.wildlife.pop(i)
        return None
    
    def add_wildlife(self, animal: Wildlife) -> None:
        """Add wildlife to this room."""
        if len(self.wildlife) < self.max_wildlife:
            self.wildlife.append(animal)
    
    def get_visible_wildlife(self) -> List[Wildlife]:
        """Get wildlife that can be seen (not elusive)."""
        return [animal for animal in self.wildlife if not animal.is_elusive()]
    
    def get_audible_wildlife(self) -> List[Wildlife]:
        """Get wildlife that can be heard."""
        return [animal for animal in self.wildlife if animal.sound_description]
    
    def _clean_wildlife_name(self, wildlife_name: str) -> str:
        """Clean wildlife name by removing articles and normalizing."""
        # Remove common articles
        articles = {"a", "an", "the"}
        words = wildlife_name.lower().split()
        words = [word for word in words if word not in articles]
        return " ".join(words)
    
    def _clean_item_name(self, item_name: str) -> str:
        """Clean item name by removing articles and normalizing."""
        # Remove common articles
        articles = {"a", "an", "the"}
        words = item_name.lower().split()
        words = [word for word in words if word not in articles]
        return " ".join(words)

    def on_enter(self, player, world_state: dict) -> None:  # noqa: ANN001
        # Hook for one-time triggers or ambient effects
        return