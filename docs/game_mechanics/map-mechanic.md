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

> *You close your eyes and retrace your steps…*

This reinforces the idea that the map is not a physical object, but a mental reconstruction of the world as it’s been explored — fitting the eerie, introspective tone of the game.

## Visual Presentation

- The map is rendered in simple ASCII.
- All connections between locations are shown with pipes (`|`, `-`).
- A **special stylistic rule** applies for three key locations:
  - `The Cabin`
  - `Konttori`
  - `Cabin Grounds`

These locations are **always connected by double pipes**, like so: = or ||

This is an intentional visual cue, subtly hinting at their shared importance and unusual behavior in the world.

## Development Notes

- The map mechanic is modular and should update dynamically as the player visits new locations.
- A location should only appear on the map if the player has visited it.
- The current player location may optionally be highlighted using a symbol (e.g. `@`) or emphasis.
- Upon exiting the map view, the room the player is in should immediately reprint its full description.