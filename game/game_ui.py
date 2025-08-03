from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.progress import Progress, BarColumn, TextColumn
from rich.text import Text

class GameUI:
    def __init__(self):
        self.console = Console()
        self.layout = Layout()
        self.layout.split(
            Layout(name="top", size=4),
            Layout(name="main", ratio=1),
            Layout(name="input", size=3)
        )
        self.health = 100
        self.fear = 0
        self.room_name = "Unknown"
        self.room_description = "..."

    def update_status(self, health, fear):
        self.health = health
        self.fear = fear

    def update_room(self, name, description):
        self.room_name = name
        self.room_description = description

    def render(self, prompt_text="What would you like to do?"):
        progress = Progress(
            TextColumn("[bold green]Health:"),
            BarColumn(bar_width=30),
            TextColumn("{task.completed} / {task.total}"),
            TextColumn("    "),
            TextColumn("[bold blue]Fear:"),
            BarColumn(bar_width=30),
            TextColumn("{task.completed} / {task.total}"),
            expand=True
        )
        progress.add_task("Health", total=100, completed=self.health)
        progress.add_task("Fear", total=100, completed=self.fear)

        self.layout["top"].update(Panel(progress, title="Status", padding=(1, 2)))
        room_panel = Panel(Text(self.room_description), title=self.room_name, padding=(1, 2))
        self.layout["main"].update(room_panel)
        self.layout["input"].update(Panel(prompt_text, title="Your Command"))

        self.console.clear()
        self.console.print(self.layout)