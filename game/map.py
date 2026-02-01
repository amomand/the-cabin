
from __future__ import annotations

from typing import Dict, Tuple, Optional

from game.location import Location
from game.room import Room
from game.requirements import WorldFlagTrue
from game.item import create_items
from game.wildlife import create_wildlife, get_random_wildlife
from game.world_state import WorldState


class Map:
    def __init__(self) -> None:
        # Global world state flags - now using typed WorldState
        self.world_state: WorldState = WorldState()
        
        # Track visited rooms
        self.visited_rooms: set = {"wilderness_start"}
        
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
            name="The Cabin Grounds",
            overview_description=(
                "The clearing opens around The Cabin, snow packed thin where feet remember paths."
            ),
        )

        cabin_interior = Location(
            location_id="cabin_interior",
            name="The Cabin",
            overview_description=(
                "Inside, old wood and stale heat. The air holds a memory of smoke."
            ),
        )

        # Rooms
        start_room = Room(
            name="Wilderness",
            description=(
                "You stand at the edge of your family's forest, where the gravel road thins into a winding track and vanishes beneath the trees. "
                "The air is cold, and still. Behind you, the rented car clicks as it cools. Ahead, a wall of pine and birch closes in, tall, dark and familiar. "
                "Somewhere past them lies the cabin — yours now, though it never quite feels like it. You hadn’t planned to come back, not this year. But a blur across the northern camera, followed by silence, was enough. "
                "No signal from the other feeds. Nothing since. So here you are, boot soles crunching on frosted ground, phone in your pocket searching for signal, and ten acres of wilderness between you and whatever waits beyond the bend."
            ),
            room_id="wilderness_start",
            items=[self.items["stick"], self.items["stone"]],  # Add some items to wilderness
            wildlife=get_random_wildlife(self.wildlife, max_count=1),  # Add random wildlife
            max_wildlife=1,
            wildlife_pool=self.wildlife,
        )

        clearing = Room(
            name="The Clearing",
            description=(
                "You can see the faint outline of The Cabin ahead, blurred by distance and dark."
            ),
            room_id="cabin_clearing",
            items=[self.items["rope"]],  # Add rope to clearing
            wildlife=get_random_wildlife(self.wildlife, max_count=1),  # Add random wildlife
            max_wildlife=1,
            wildlife_pool=self.wildlife,
        )

        cabin = Room(
            name="The Cabin",
            description=(
                "You are inside a small cabin. You take a deep breath, inhaling the scent of wood.\n"
                "As you exhale, familiarity wraps around you.\n\nThis is your cabin\n\n"
                "A door leads to the konttori (office)."
            ),
            room_id="cabin_main",
            items=[self.items["matches"], self.items["key"], self.items["light switch"], self.items["fireplace"]],  # Add items to cabin
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

        cabin_grounds_room = Room(
            name="Cabin Grounds",
            description=(
                "The area around The Cabin. Snow is packed thin where feet remember paths.\n"
                "A woodshed stands nearby, its door slightly ajar."
            ),
            room_id="cabin_grounds_main",
            items=[self.items["firewood"]],  # Move firewood to cabin grounds
            wildlife=get_random_wildlife(self.wildlife, max_count=1),  # Add random wildlife
            max_wildlife=1,
            wildlife_pool=self.wildlife,
        )

        lakeside = Room(
            name="Lakeside",
            description=(
                "You stand by the edge of a dark lake. The water is still and black.\n"
                "A path leads further into the woods."
            ),
            room_id="lakeside",
            items=[],  # Remove firewood from lakeside
            wildlife=get_random_wildlife(self.wildlife, max_count=1),  # Add random wildlife
            max_wildlife=1,
            wildlife_pool=self.wildlife,
        )

        wood_track = Room(
            name="Wood Track",
            description=(
                "A narrow track winds through the dense woods. The trees press close on either side.\n"
                "The path is well-worn but overgrown in places."
            ),
            room_id="wood_track",
            items=[self.items["knife"]],  # Add knife to wood track
            wildlife=get_random_wildlife(self.wildlife, max_count=2),  # More wildlife in deeper woods
            max_wildlife=2,
            wildlife_pool=self.wildlife,
        )

        old_woods = Room(
            name="Old Woods",
            description=(
                "Ancient trees tower overhead, their branches interlocking to form a dark canopy.\n"
                "The air is thick with the scent of moss and decay. This place feels old, older than memory."
            ),
            room_id="old_woods",
            items=[self.items["amulet"]],  # Add amulet to old woods
            wildlife=get_random_wildlife(self.wildlife, max_count=2),  # More wildlife in deepest woods
            max_wildlife=2,
            wildlife_pool=self.wildlife,
        )

        # Optional example: gate leaving the cabin interior unless power restored (diegetic placeholder)
        # Not applied globally here; instead, we add a requirement on a specific exit if desired.

        # Register rooms to locations
        wilderness.add_room(start_room)
        cabin_grounds.add_room(clearing)
        cabin_grounds.add_room(cabin_grounds_room)
        cabin_grounds.add_room(lakeside)
        cabin_grounds.add_room(wood_track)
        cabin_grounds.add_room(old_woods)
        cabin_interior.add_room(cabin)
        cabin_interior.add_room(konttori)

        # Room-level exits: direction -> (target_location_id, target_room_id)
        # Linear progression: Wilderness -> Clearing -> Cabin -> Konttori -> Cabin Grounds -> Lakeside -> Wood Track -> Old Woods
        start_room.exits = {"north": ("cabin_grounds", "cabin_clearing")}
        clearing.exits = {
            "south": ("wilderness", "wilderness_start"),
            "cabin": ("cabin_interior", "cabin_main"),
        }
        cabin.exits = {
            "out": ("cabin_grounds", "cabin_clearing"),
            "north": ("cabin_interior", "konttori"),
        }
        konttori.exits = {
            "south": ("cabin_interior", "cabin_main"),
            "north": ("cabin_grounds", "cabin_grounds_main"),
        }
        cabin_grounds_room.exits = {
            "south": ("cabin_interior", "konttori"),
            "north": ("cabin_grounds", "lakeside"),
            "clearing": ("cabin_grounds", "cabin_clearing"),
        }
        lakeside.exits = {
            "south": ("cabin_grounds", "cabin_grounds_main"),
            "north": ("cabin_grounds", "wood_track"),
            "grounds": ("cabin_grounds", "cabin_grounds_main"),
        }
        wood_track.exits = {
            "south": ("cabin_grounds", "lakeside"),
            "north": ("cabin_grounds", "old_woods"),
            "lakeside": ("cabin_grounds", "lakeside"),
        }
        old_woods.exits = {
            "south": ("cabin_grounds", "wood_track"),
            "track": ("cabin_grounds", "wood_track"),
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
        return self.locations[self.current_location_id].rooms[self.current_room_id]

    def move(self, direction: str, player=None) -> Tuple[bool, str]:
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
            if not requirement.is_met(player, self.world_state):
                return False, requirement.denial_text(player, self.world_state)

        target_location_id, target_room_id = room.exits[direction]

        # Move
        self.current_location_id = target_location_id
        self.current_room_id = target_room_id

        # Mark the new room as visited
        self.visited_rooms.add(target_room_id)

        # Trigger on-enter hooks
        self.current_room.on_enter(player, self.world_state)

        return True, ""

    def display_map(self, visited_rooms: set) -> str:
        """Display an ASCII map of visited areas.
        
        Args:
            visited_rooms: Set of room IDs the player has visited
            
        Returns:
            ASCII map string
        """
        # Define the room layout and connections
        room_layout = [
            ("wilderness_start", "The Wilderness"),
            ("cabin_clearing", "The Clearing"),
            ("cabin_main", "The Cabin"),
            ("konttori", "Konttori"),
            ("cabin_grounds_main", "Cabin Grounds"),
            ("lakeside", "Lakeside"),
            ("wood_track", "Wood Track"),
            ("old_woods", "Old Woods")
        ]
        
        # Special locations that use double pipes
        special_locations = {"cabin_main", "konttori", "cabin_grounds_main"}
        
        map_lines = []
        
        for i, (room_id, room_name) in enumerate(room_layout):
            # Only show visited rooms
            if room_id not in visited_rooms:
                continue
                
            # Add room name
            map_lines.append(room_name)
            
            # Add connection to next room (if there is one and it's visited)
            if i < len(room_layout) - 1:
                next_room_id = room_layout[i + 1][0]
                if next_room_id in visited_rooms:
                    # Use double pipes ONLY when BOTH rooms are special locations
                    if room_id in special_locations and next_room_id in special_locations:
                        map_lines.append("||")
                    else:
                        map_lines.append(" |")
                else:
                    # No connection if next room not visited
                    map_lines.append("")
            else:
                # Last room has no connection
                map_lines.append("")
        
        # Filter out empty lines and join
        map_lines = [line for line in map_lines if line.strip()]
        
        return "\n".join(map_lines)

    def get_visited_rooms(self) -> set:
        """Get a set of all room IDs that have been visited."""
        return self.visited_rooms.copy()

    def _set_current_room_by_id(self, room_id: str) -> bool:
        """
        Set current room by ID (for save/load).
        
        Returns True if room was found and set, False otherwise.
        """
        for location in self.locations.values():
            if room_id in location.rooms:
                self.current_location = location
                self.current_room = location.rooms[room_id]
                return True
        return False
