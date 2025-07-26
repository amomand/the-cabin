class Room:
    def __init__(self, name, description):
        self.name = name
        self.description = description
        self.exits = {}  # e.g., {'north': another_room}