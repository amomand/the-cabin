from game.room import Room

class Map:
    def __init__(self):
        self.name = "The Wilderness"
        self.description = (
            "You are in the wilderness.\n"
            "All around you, the trees lean close, silent and unmoving. A narrow path winds north."
        )

        # Create rooms
        self.start_room = Room(
            "Wilderness",self.description)
        self.cabin_room = Room(
            "Cabin Clearing",
            "You can see the faint outline of a cabin ahead,\nblurred by distance and dark.")
            
        # Set up exits
        self.start_room.exits = {"north": self.cabin_room}
        self.cabin_room.exits = {"south": self.start_room}

        # List of all rooms (optional, for reference)
        self.locations = [self.start_room, self.cabin_room]

        # The current room the player is in
        self.current_room = self.start_room