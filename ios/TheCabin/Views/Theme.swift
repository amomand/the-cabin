import SwiftUI

/// Dark, terse, monospaced. The screen should feel like a cold room, not an app.
enum Theme {
    static let background = Color.black
    static let narration = Color(white: 0.88)
    /// The player's own words sit back from the prose.
    static let echo = Color(white: 0.42)
    /// Refusals are still the world speaking, so they read as prose rather than
    /// as an error: dimmed, never red, never boxed.
    static let refusal = Color(white: 0.62)
    static let statusLabel = Color(white: 0.35)
    static let statusValue = Color(white: 0.7)
    static let rule = Color(white: 0.16)

    static let font = Font.system(.body, design: .monospaced)
    static let statusFont = Font.system(.caption, design: .monospaced)

    static func colour(for kind: TranscriptBlock.Kind) -> Color {
        switch kind {
        case .narration: return narration
        case .echo: return echo
        case .refusal: return refusal
        }
    }
}
