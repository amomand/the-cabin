from __future__ import annotations
from typing import Set, Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class Item:
    """An item that can be found in rooms or carried by the player."""
    
    name: str
    description: str
    traits: Set[str]  # carryable, usable, throwable, weapon, flammable, edible, cursed
    room_description: str  # How it appears in room descriptions
    
    def __init__(
        self,
        name: str,
        description: str,
        traits: Set[str] = None,
        room_description: Optional[str] = None
    ):
        self.name = name
        self.description = description
        self.traits = traits or set()
        self.room_description = room_description or f"A {name}."
    
    def has_trait(self, trait: str) -> bool:
        """Check if the item has a specific trait."""
        return trait in self.traits
    
    def is_carryable(self) -> bool:
        """Check if the item can be picked up."""
        return "carryable" in self.traits
    
    def is_usable(self) -> bool:
        """Check if the item can be used."""
        return "usable" in self.traits
    
    def is_throwable(self) -> bool:
        """Check if the item can be thrown."""
        return "throwable" in self.traits
    
    def is_weapon(self) -> bool:
        """Check if the item can be used as a weapon."""
        return "weapon" in self.traits
    
    def is_flammable(self) -> bool:
        """Check if the item can catch fire."""
        return "flammable" in self.traits
    
    def is_edible(self) -> bool:
        """Check if the item can be consumed."""
        return "edible" in self.traits
    
    def is_cursed(self) -> bool:
        """Check if the item has supernatural effects."""
        return "cursed" in self.traits
    
    def __str__(self) -> str:
        return self.name
    
    def __repr__(self) -> str:
        return f"Item('{self.name}', traits={self.traits})"


# Predefined items for the game
def create_items() -> Dict[str, Item]:
    """Create a dictionary of predefined items for The Cabin."""
    items = {}
    
    # Basic survival items
    items["rope"] = Item(
        name="rope",
        description="A length of sturdy rope, weathered but strong.",
        traits={"carryable", "usable", "throwable"},
        room_description="A coiled rope lies on the ground."
    )
    
    items["matches"] = Item(
        name="matches",
        description="A small box of wooden matches. The striking surface is worn.",
        traits={"carryable", "usable", "flammable"},
        room_description="A matchbox sits on the surface."
    )
    
    items["key"] = Item(
        name="key",
        description="A rusted iron key, cold to the touch.",
        traits={"carryable", "usable"},
        room_description="A rusted key glints in the dim light."
    )
    
    items["stone"] = Item(
        name="stone",
        description="A smooth river stone, heavy in your hand.",
        traits={"carryable", "throwable", "weapon"},
        room_description="A smooth stone rests on the ground."
    )
    
    items["stick"] = Item(
        name="stick",
        description="A dry branch, brittle but useful.",
        traits={"carryable", "throwable", "flammable"},
        room_description="A dry stick lies nearby."
    )
    
    items["knife"] = Item(
        name="knife",
        description="A hunting knife with a bone handle. The blade is sharp.",
        traits={"carryable", "usable", "weapon"},
        room_description="A hunting knife sits on the surface."
    )
    
    items["berries"] = Item(
        name="berries",
        description="A handful of dark berries. They look edible but you're not sure.",
        traits={"carryable", "edible"},
        room_description="Dark berries grow on a nearby bush."
    )
    
    items["amulet"] = Item(
        name="amulet",
        description="An ancient amulet with strange markings. It feels wrong.",
        traits={"carryable", "cursed"},
        room_description="An amulet with strange markings hangs from a branch."
    )
    
    # Quest-related items
    items["firewood"] = Item(
        name="firewood",
        description="Dry logs, perfect for burning. They'll keep you warm.",
        traits={"carryable", "flammable"},
        room_description="A stack of dry firewood is piled neatly."
    )
    
    items["circuit_breaker"] = Item(
        name="circuit breaker",
        description="The main electrical panel. The main breaker is in the OFF position.",
        traits={"usable"},
        room_description="A circuit breaker panel is mounted on the wall."
    )
    
    return items
