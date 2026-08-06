"""The cues that frame a full-screen overlay, shared by both surfaces.

The quest screen, the map and the cutscenes all interrupt the room to show
something, and each is wrapped in a line that takes the player out of the room
and a line that puts them back. Both surfaces print them, so both surfaces have
to print the *same* ones.

They lived as literals in `GameEngine` and `WebGameSession` separately, and had
already drifted: the terminal's map cue ended in a `…` and the web's in three
dots, so the two surfaces disagreed about a character in the one line that says
"stop reading the room". The differential playtest scenario caught it, which is
what that scenario is for; putting the strings here is what stops it happening
again.

`CUTSCENE_DISMISS_TEXT` stays in `game/cutscene.py`, next to the class that
blocks on the keypress it describes.
"""

QUEST_SCREEN_ENTER = "*You take a breath and focus...*"
QUEST_SCREEN_EXIT = "*Hold the thought.*"

MAP_SCREEN_ENTER = "*You close your eyes and retrace your steps...*"
MAP_SCREEN_EXIT = "*Open your eyes.*"
