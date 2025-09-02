# Cut-Scene Mechanic

## Overview

The cut-scene mechanic provides a way to display atmospheric, narrative text that interrupts normal gameplay to immerse the player in key moments of the story. Cut-scenes are triggered by specific game events and require player interaction to continue.

## Behavior

### Display
- **Terminal Clear**: The screen is completely cleared before displaying cut-scene text
- **Full Text Display**: The entire cut-scene text is displayed at once for the player to read
- **Atmospheric Formatting**: Text is formatted with decorative borders and proper spacing
- **Wait for Input**: After displaying, the game waits for any key press to continue
- **Screen Clear**: After the player presses a key, the screen is cleared again and normal gameplay resumes

### Triggering
- Cut-scenes are triggered by specific game events (currently movement between rooms)
- Each cut-scene has a trigger condition that determines when it should play
- Cut-scenes only play once per game session (unless reset for testing)
- Multiple cut-scenes can be triggered by the same event

### Integration
- Cut-scenes are checked after successful movement between rooms
- They play before the new room description is shown
- The game state is preserved during cut-scene playback
- Cut-scenes don't interfere with normal game mechanics

## Implementation

### File Structure

Cut-scenes are stored as individual markdown files in the `docs/lore/cutscenes/` folder:

```
docs/
  lore/
    cutscenes/
      entering-cabin.md      # Cut-scene for entering the cabin
      future-cutscene.md     # Future cut-scenes...
```

Each cut-scene file follows this format:
- **Title**: First line with the cut-scene name
- **Metadata**: Optional trigger description
- **Content**: The actual cut-scene text between decorative borders

### Core Classes

#### `Cutscene`
Represents a single cut-scene with:
- **text**: The narrative text to display
- **trigger_condition**: Optional function that determines when to trigger
- **has_played**: Boolean flag to prevent replaying

#### `CutsceneManager`
Manages all cut-scenes in the game:
- **cutscenes**: List of all available cut-scenes
- **check_and_play_cutscenes()**: Main method to check and trigger cut-scenes
- **add_cutscene()**: Method to add new cut-scenes
- **reset_all_cutscenes()**: Method to reset all cut-scenes (for testing)

### Adding New Cut-Scenes

1. **Create a markdown file** in `docs/lore/cutscenes/`:
   ```markdown
   # Cut-scene Title
   
   **Trigger**: Brief description of when this triggers
   
   ───────────────────────────────────────────────────────────────────────────────
   
   Your atmospheric text here.
   
   Multiple paragraphs are supported.
   
   Use proper formatting for readability.
   
   ───────────────────────────────────────────────────────────────────────────────
   ```

2. **Define a trigger condition** in `cutscene.py`:
   ```python
   def my_trigger_condition(from_room_id: str, to_room_id: str, **kwargs) -> bool:
       # Return True when the cut-scene should trigger
       return from_room_id == "some_room" and to_room_id == "target_room"
   ```

3. **Load the cut-scene** in `CutsceneManager._setup_cutscenes()`:
   ```python
   self._load_cutscene_from_file("filename-without-extension", self._my_trigger_condition)
   ```

### Trigger Conditions

Cut-scenes can be triggered by various game events. Currently supported:

- **Room Movement**: Triggered when moving from one room to another
  - Parameters: `from_room_id`, `to_room_id`, `player`, `world_state`

Future trigger types could include:
- **Item Interactions**: When picking up or using specific items
- **Wildlife Encounters**: When encountering certain animals
- **World State Changes**: When specific flags are set
- **Player State**: When health/fear reaches certain thresholds
- **Time-based**: After spending certain time in areas

### Example Cut-Scene

The cabin entry cut-scene demonstrates the mechanic:

**File**: `docs/lore/cutscenes/entering-cabin.md`
```markdown
# Entering the Cabin

**Trigger**: Moving from the clearing to the cabin interior

───────────────────────────────────────────────────────────────────────────────

The door groaned the same way it always had — low, drawn out, like something
being woken that preferred to stay sleeping...

[Full text continues...]
```

**Trigger Function** (in `cutscene.py`):
```python
def _cabin_entry_trigger(self, from_room_id: str, to_room_id: str, **kwargs) -> bool:
    """Trigger when moving from the clearing to the cabin interior."""
    return from_room_id == "cabin_clearing" and to_room_id == "cabin_main"
```

**Loading** (in `CutsceneManager._setup_cutscenes()`):
```python
self._load_cutscene_from_file("entering-cabin", self._cabin_entry_trigger)
```

This cut-scene triggers when the player moves from the "The Clearing" room to the "The Cabin" room, displaying Eli's memory of the cabin and the mysterious events from her childhood.

## Best Practices

### Writing Cut-Scene Text
- **Atmospheric**: Use descriptive, mood-setting language
- **Concise**: Keep text focused and impactful
- **Readable**: Use proper paragraph breaks and formatting
- **Diegetic**: Keep text in-world and consistent with the game's tone
- **Pacing**: Consider the emotional impact and timing

### Trigger Design
- **Specific**: Make triggers precise to avoid unwanted activations
- **Meaningful**: Only trigger cut-scenes for significant moments
- **Non-intrusive**: Don't overuse cut-scenes; they should feel special
- **Contextual**: Consider the player's current state and recent actions

### Technical Considerations
- **Performance**: Cut-scenes are lightweight and don't impact game performance
- **State Preservation**: Game state is maintained during cut-scene playback
- **Error Handling**: Cut-scenes gracefully handle terminal compatibility issues
- **Testing**: Use `reset_all_cutscenes()` to test cut-scenes multiple times

## Future Enhancements

Potential improvements to the cut-scene system:

1. **Visual Effects**: Add typing effects, color, or ASCII art
2. **Audio Cues**: Add sound effects or ambient audio
3. **Branching**: Allow cut-scenes to have multiple outcomes based on player choices
4. **Timing**: Add automatic progression after a certain time
5. **Skippable**: Allow players to skip cut-scenes they've seen before
6. **Save State**: Remember which cut-scenes have been seen across game sessions
7. **Conditional Text**: Show different text based on player state or world flags
