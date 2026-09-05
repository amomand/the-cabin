import Foundation

/// The cold-launch cover used only when a persisted run has moved beyond its
/// real opening frame.
///
/// New runs render the opening `RenderFrame` from the transport, and its lines
/// are cached for later launches. These literals exist only to migrate runs
/// saved before that cache existed. The Python parity test pins them byte for
/// byte to `game.intro.INTRO_LINES` so this fallback cannot become another
/// source of story truth.
enum LaunchOpener {
    static let legacyFallbackLines: [String] = [
        "You shouldn't have come back. It's awake. It always has been.",
    ]
}
