from __future__ import annotations

from typing import Dict, Tuple

from game.location import Location
from game.room import Room
from game.requirements import WorldFlagTrue
from game.item import create_items
from game.wildlife import create_wildlife, get_random_wildlife


class Map:
    def __init__(self) -> None:
        # Global world state flags; extend as needed (weather, time_of_day, etc.)
        self.world_state: Dict[str, object] = {
            "has_power": False,
        }
        
        # Create items and wildlife for the game
        self.items = create_items()
        self.wildlife = create_wildlife()

        # Build locations and rooms
        wilderness = Location(
            location_id="wilderness",
            name="The Wilderness",
            overview_description=(
                "You are in the wilderness. The trees lean close, silent and unmoving."
            ),
        )

        cabin_grounds = Location(
            location_id="cabin_grounds",
            name="Cabin Grounds",
            overview_description=(
                "The clearing opens around the old cabin, snow packed thin where feet remember paths."
            ),
        )

        cabin_interior = Location(
            location_id="cabin_interior",
            name="Cabin Interior",
            overview_description=(
                "Inside, old wood and stale heat. The air holds a memory of smoke."
            ),
        )

        # Rooms
        start_room = Room(
            name="Wilderness",
            description=(
                "You are in the wilderness.\n"
                "All around you, the trees lean close, silent and unmoving. A narrow path winds north."
            ),
            room_id="wilderness_start",
            items=[self.items["stick"], self.items["stone"]],  # Add some items to wilderness
            wildlife=get_random_wildlife(self.wildlife, max_count=1),  # Add random wildlife
            max_wildlife=1,
            wildlife_pool=self.wildlife,
        )

        clearing = Room(
            name="Cabin Clearing",
            description=(
                "You can see the faint outline of a cabin ahead, blurred by distance and dark."
            ),
            room_id="cabin_clearing",
            items=[self.items["rope"]],  # Add rope to clearing
            wildlife=get_random_wildlife(self.wildlife, max_count=1),  # Add random wildlife
            max_wildlife=1,
            wildlife_pool=self.wildlife,
        )

        cabin = Room(
            name="Cabin",
            description=(
                "You are inside a small cabin. You take a deep breath, inhaling the scent of wood.\n"
                "As you exhale, familiarity wraps around you.\n\nThis is your cabin"
            ),
            room_id="cabin_main",
            items=[self.items["matches"], self.items["key"]],  # Add items to cabin
            wildlife=[],  # No wildlife inside the cabin
            max_wildlife=0,
            wildlife_pool={},
        )

        konttori = Room(
            name="Konttori",
            description=(
                "A small office space. Papers are scattered across a desk.\n"
                "The circuit breaker panel hums quietly on the wall."
            ),
            room_id="konttori",
            items=[self.items["circuit_breaker"]],  # Add circuit breaker to konttori
            wildlife=[],  # No wildlife in the office
            max_wildlife=0,
            wildlife_pool={},
        )

        lakeside = Room(
            name="Lakeside",
            description=(
                "You stand by the edge of a dark lake. The water is still and black.\n"
                "A woodshed stands nearby, its door slightly ajar."
            ),
            room_id="lakeside",
            items=[self.items["firewood"]],  # Add firewood to lakeside
            wildlife=get_random_wildlife(self.wildlife, max_count=1),  # Add random wildlife
            max_wildlife=1,
            wildlife_pool=self.wildlife,
        )

        # Optional example: gate leaving the cabin interior unless power restored (diegetic placeholder)
        # Not applied globally here; instead, we add a requirement on a specific exit if desired.

        # Register rooms to locations
        wilderness.add_room(start_room)
        cabin_grounds.add_room(clearing)
        cabin_grounds.add_room(lakeside)
        cabin_interior.add_room(cabin)
        cabin_interior.add_room(konttori)

        # Room-level exits: direction -> (target_location_id, target_room_id)
        start_room.exits = {"north": ("cabin_grounds", "cabin_clearing")}
        clearing.exits = {
            "south": ("wilderness", "wilderness_start"),
            "cabin": ("cabin_interior", "cabin_main"),
            "lakeside": ("cabin_grounds", "lakeside"),
        }
        cabin.exits = {
            "out": ("cabin_grounds", "cabin_clearing"),
            "konttori": ("cabin_interior", "konttori"),
        }
        konttori.exits = {
            "cabin": ("cabin_interior", "cabin_main"),
        }
        lakeside.exits = {
            "clearing": ("cabin_grounds", "cabin_clearing"),
        }

        # Map registries
        self.locations: Dict[str, Location] = {
            wilderness.id: wilderness,
            cabin_grounds.id: cabin_grounds,
            cabin_interior.id: cabin_interior,
        }

        # Starting position
        self.current_location_id = wilderness.id
        self.current_room_id = start_room.id

    @property
    def current_location(self) -> Location:
        return self.locations[self.current_location_id]

    @property
    def current_room(self) -> Room:
        return self.current_location.rooms[self.current_room_id]

    def move(self, direction: str) -> Tuple[bool, str]:
        """Attempt to move in a direction. Returns (moved, message).

        - Checks room-level `exit_criteria` in order.
        - Performs cross-location transition when target location differs.
        - Returns diegetic denial text on failure.
        """
        room = self.current_room
        if direction not in room.exits:
            return False, "You turn that way and stop. Just trees and dark."

        # Check room exit criteria (if any)
        for requirement in room.exit_criteria:
            if not requirement.is_met(None, self.world_state):  # Player is not needed yet
                return False, requirement.denial_text(None, self.world_state)

        target_location_id, target_room_id = room.exits[direction]

        # Move
        self.current_location_id = target_location_id
        self.current_room_id = target_room_id

        # Trigger on-enter hooks
        self.current_room.on_enter(None, self.world_state)  # Player is optional for now

        return True, ""