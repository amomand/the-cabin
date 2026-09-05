from __future__ import annotations
from typing import Set, Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class Item:
    """An item that can be found in rooms or carried by the player."""
    
    name: str
    description: str
    traits: Set[str]  # carryable, usable, throwable, weapon, flammable, edible, cursed, person
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
        # An explicit empty string suppresses the item from room listings
        # (used by wrong-layer fixtures). Only None falls back to a generic label.
        self.room_description = (
            f"A {name}." if room_description is None else room_description
        )
    
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

    def is_person(self) -> bool:
        """Check if this entry stands for a person rather than an object."""
        return "person" in self.traits

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
        description="Grey utility rope, stiff with frost but sound under the weathering.",
        traits={"carryable", "usable", "throwable"},
        room_description="A coil of grey rope lies stiff with frost."
    )
    
    items["matches"] = Item(
        name="matches",
        description="A half-used matchbox. The striker is worn pale in the middle.",
        traits={"carryable", "usable", "flammable"},
        room_description="A half-used matchbox is within reach."
    )
    
    items["key"] = Item(
        name="key",
        description="The cabin key, blackened at the bow and rough with rust.",
        traits={"carryable", "usable"},
        room_description="The black-bowed cabin key lies by itself."
    )
    
    items["stone"] = Item(
        name="stone",
        description="A fist-sized stone, smooth on one side and split sharp on the other.",
        traits={"carryable", "throwable", "weapon"},
        room_description="A fist-sized stone lies nearby, split sharp on one side."
    )
    
    items["stick"] = Item(
        name="stick",
        description="A snapped birch branch, dry under the bark.",
        traits={"carryable", "throwable", "flammable"},
        room_description="A snapped birch branch lies with pale wood showing."
    )
    
    items["berries"] = Item(
        name="berries",
        description="Black berries wrinkled by the first hard frost.",
        traits={"carryable", "edible"},
        room_description="Frost-wrinkled black berries lie in a dark little spill."
    )
    
    # Quest-related items
    items["firewood"] = Item(
        name="firewood",
        description="Split pine, seasoned under the woodshed roof.",
        traits={"carryable", "flammable"},
        room_description="Split logs are stacked under the woodshed roof."
    )
    
    items["circuit_breaker"] = Item(
        name="circuit breaker",
        description="The main breaker has tripped. The switch rests in the OFF position.",
        traits={"usable"},
        room_description=""
    )
    
    # Interactive room features
    items["light switch"] = Item(
        name="light switch",
        description="The old white switch by the door. It gives under your finger.",
        traits={"usable"},
        room_description="The old white switch waits by the door."
    )
    
    items["fireplace"] = Item(
        name="fireplace",
        description="The stone hearth, swept bare and cold through.",
        traits={"usable"},
        room_description=""
    )

    items["phone"] = Item(
        name="phone",
        description=(
            "Your phone. Nika's voicemail is still on the screen, eleven days old. "
            "You know the message by heart."
        ),
        traits={"usable"},
        room_description="",
    )

    items["camera feed"] = Item(
        name="camera feed",
        description=(
            "The five frames saved on your phone, five weeks old."
        ),
        traits={"usable"},
        room_description="",
    )

    items["bed"] = Item(
        name="bed",
        description=(
            "The old bed, made up under heavy covers. The blankets still hold the year's cold."
        ),
        traits={"usable"},
        room_description="",
    )

    items["sauna stove"] = Item(
        name="sauna stove",
        description=(
            "The iron stove in the sauna, stones stacked on top. It takes time to heat. "
            "A bucket and ladle wait beside it."
        ),
        traits={"usable"},
        room_description="",
    )

    # Wrong-layer fixtures. Their room_description is empty so they never show up in the
    # real cabin's look output. They are addressable ("use window", "talk nika") but
    # only yield narrative in the wrong layer. See UseAction.
    items["window"] = Item(
        name="window",
        description=(
            "The small cabin window. Frost has patterned across the inside of the glass."
        ),
        traits={"usable"},
        room_description="",
    )
    items["mug"] = Item(
        name="mug",
        description="A mug of coffee, made exactly how you take it.",
        traits={"usable"},
        room_description="",
    )
    items["nika"] = Item(
        name="nika",
        description=(
            "Nika. Your oldest friend. She looks tired, and slightly annoyed in the way that means frightened."
        ),
        # `person` keeps the inventory machinery from answering for her. She is
        # addressable because Act III turns on talking to her; she is not a
        # fixture to be lifted, and must never be narrated as one.
        traits={"usable", "person"},
        room_description="",
    )
    items["mattress"] = Item(
        name="mattress",
        description=(
            "The spare mattress from the chest, the one that has lived there "
            "since before either of you could carry it."
        ),
        traits={"usable"},
        room_description="",
    )
    items["tins"] = Item(
        name="tins",
        description="Dinner tins, stacked by the stove. You don't remember buying them.",
        traits={"usable"},
        room_description="",
    )

    items["table"] = Item("table", "The square table where you eat.", {"usable"}, "")
    items["monitor"] = Item("monitor", "The security monitor on the desk.", {"usable"}, "")
    items["northern camera"] = Item("northern camera", "The battery camera on the north eave.", {"usable"}, "")
    return items
