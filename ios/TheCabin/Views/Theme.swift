import SwiftUI

/// Dark, terse, and bookish. The screen should feel like a cold room, not an app.
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

    /// The web surface starts with Iowan Old Style too. Using the face built
    /// into iOS keeps the two surfaces aligned without shipping a font file,
    /// while `relativeTo` preserves Dynamic Type scaling.
    static let bookFontName = "IowanOldStyle-Roman"
    static let font = Font.custom(bookFontName, size: 17, relativeTo: .body)
    static let statusFont = Font.system(.caption, design: .monospaced)

    static func colour(for kind: TranscriptBlock.Kind) -> Color {
        switch kind {
        case .narration: return narration
        case .echo: return echo
        case .refusal: return refusal
        }
    }
}
