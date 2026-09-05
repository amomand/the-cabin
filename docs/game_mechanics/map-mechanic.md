# Map Mechanic

## Overview

The map mechanic allows players to view a growing, ASCII-rendered map of the areas they have explored. It is designed to enhance immersion and spatial awareness without breaking the tone of the game.

## Player Interaction

- To view the map, players can type `m` or `map` into the prompt.
- The screen will clear, and a rendered ASCII map will be shown.
- The map will only display **areas the player has already visited**.
- After viewing the map, **any key press** will dismiss it, clear the screen, and reprint the current room description.

## Narrative Framing

When the map is triggered, instead of a standard UI label, the player will be shown the text:

> *You retrace the route in your head.*

This keeps the map a mental reconstruction of the route rather than a physical object Elli carries.

## Visual Presentation

North is at the top of the main approach. The woods now run from the grounds
through the treeline and Dead Pines into Old Woods. The optional lake walk is
a loop joining the same treeline; the inlet remains a dead end. Connections use
ordinary ASCII lines and appear only when both endpoint rooms are known.

The diagram is a remembered route, not a surveyed floor plan. The konttori
connects only to the main room. Room ids remain stable for saves: `wood_track`
is The Treeline, and `deer_path` is Dead Pines. The deer path of the story is
absent when Elli reaches its old entrance in Old Woods.

## Development Notes

- The map mechanic is modular and should update dynamically as the player visits new locations.
- A location should only appear on the map if the player has visited it.
- A connector should only appear if both endpoint rooms have been visited.
- The current player location may optionally be highlighted using a symbol (e.g. `@`) or emphasis.
- Upon exiting the map view, the room the player is in should immediately reprint its full description.
