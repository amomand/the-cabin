class Game:
    def __init__(self):
        self.running = True
        self.player = ...  # Load or create player
        self.map = ...     # Generate map

    def run(self):
        print("You stand at the edge of the wilderness.")
        while self.running:
            print("\n" + self.map.describe_current_location())
            command = input("> ").strip().lower()
            self.handle_command(command)

    def handle_command(self, command):
        if command in ["quit", "exit"]:
            self.running = False
        else:
            # Dispatch command to player or map
            ...