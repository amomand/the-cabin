import SwiftUI

/// Dark, terse, and bookish. The screen should feel like a cold room, not an app.
enum Theme {
    static let background = Color.black
    static let narration = Color(white: 0.88)
    /// Room names sit a shade brighter than the prose under them.
    static let title = Color(white: 0.94)
    /// The player's own words sit back from the prose.
    static let echo = Color(white: 0.42)
    /// Refusals are still the world speaking, so they read as prose rather than
    /// as an error: dimmed, never red, never boxed.
    static let refusal = Color(white: 0.62)
    /// Asides and dismiss cues, set in italic and a little back from the prose.
    static let aside = Color(white: 0.6)
    static let statusLabel = Color(white: 0.35)
    static let statusValue = Color(white: 0.7)
    static let rule = Color(white: 0.16)

    /// The web surface starts with Iowan Old Style too. Using the face built
    /// into iOS keeps the two surfaces aligned without shipping a font file,
    /// while `relativeTo` preserves Dynamic Type scaling.
    static let bookFontName = "IowanOldStyle-Roman"
    static let bookItalicFontName = "IowanOldStyle-Italic"
    static let bookBoldFontName = "IowanOldStyle-Bold"
    static let font = Font.custom(bookFontName, size: 17, relativeTo: .body)
    static let asideFont = Font.custom(bookItalicFontName, size: 17, relativeTo: .body)
    static let titleFont = Font.custom(bookBoldFontName, size: 19, relativeTo: .title3)
    static let statusFont = Font.system(.caption, design: .monospaced)

    /// Horizontal inset for prose and the command line, shared so the echo
    /// under the transcript and the prompt below it sit on one margin.
    static let inset: CGFloat = 20
    /// Extra leading between lines of prose. The book face sets tight on its
    /// own; this brings it to roughly the browser surface's line height.
    static let leading: CGFloat = 5
    /// The height of an empty line from the turn core: a paragraph break.
    static let paragraphGap: CGFloat = 10
    /// The short hairline drawn under a room name or in place of a long rule.
    static let ruleWidth: CGFloat = 64

    static func colour(for kind: TranscriptBlock.Kind) -> Color {
        switch kind {
        case .narration: return narration
        case .echo: return echo
        case .refusal: return refusal
        }
    }
}
