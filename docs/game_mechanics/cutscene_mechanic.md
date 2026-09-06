# Cutscenes

Cutscenes interrupt play with authored text before the destination room is
shown. The movement listener checks the registered transition conditions;
played identities prevent replay. Terminal and web wait for dismissal before
continuing. Each scene supplies its own `dismiss_text` cue from
`CUTSCENE_DISMISS_CUES`; closing web frames remove cues that cannot be acted on.

The flight belongs in this channel because ordinary move feedback renders
after the room. Narrating the run there would show the false-cabin arrival
before the flight that caused it. Its trigger is specifically
`old_woods -> cabin_main`; a broader cabin-entry trigger could replay it in the
wrong act. [World layers](world-layers-mechanic.md) owns the transition itself.

## Asset and identity contract

Runtime assets live in [game/story/cutscenes/](../../game/story/cutscenes/).
Each contains only player-visible fiction and the opening/closing 79-character
rules. Contributor titles and trigger notes belong outside the payload. Missing
or unreadable required files, invalid UTF-8, missing framing and an empty body
fail startup; a story transition must never silently lose its narration.

Register the asset and its precise trigger in
[CutsceneManager](../../game/cutscene.py). The source filename is its stable
`cutscene_id`: renaming it re-arms the scene in existing saves. Never derive an
identity from prose, since shared opening rules once made distinct scenes
indistinguishable. Duplicate registration is rejected. The
[save/load contract](save-load-mechanic.md) owns older-identity handling and
replacement of played history.

For a new scene, verify trigger specificity, dismissal and ordering alongside
any quest opened by the same movement. The cutscene listener must run before
the quest listener, as specified by the [event bus](../architecture/event-bus.md).
Use [cutscene tests](../../tests/test_cutscene.py) for the asset/trigger contract
and [both-surface scenarios](../architecture/playtesting.md) for rendered order.
Follow the bible's scene-register and paragraph rules; do not copy example prose
into runtime files or treat old proposed enhancements as implementation requirements.
