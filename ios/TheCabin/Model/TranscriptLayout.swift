import Foundation

/// How a transcript block should be set on the page.
///
/// Frames arrive as plain lines, and the turn core writes a few of them as a
/// terminal would: a room name followed by a row of dashes, a long rule around
/// a cutscene, a phrase wrapped in asterisks for emphasis, an empty line for a
/// paragraph break. The browser surface reads the same shapes and styles them;
/// this does the same for iOS. Nothing here changes what was said or what is
/// stored, only how it sits.
enum TranscriptRole: Equatable {
    /// Prose, the player's echo, or a narrated refusal, set as is.
    case body
    /// A room name: the line immediately before a row of dashes.
    case title
    /// A row of dashes or box-drawing, drawn as a short hairline.
    case rule
    /// A line wrapped in asterisks, set in italic with the markers dropped.
    case aside(String)
    /// An empty line: a paragraph break, not a blank row of type.
    case gap
}

extension TranscriptRole {
    /// The role of every block, in order. Title detection needs the next
    /// line, which is why this works on the whole transcript rather than one
    /// block at a time.
    static func roles(for blocks: [TranscriptBlock]) -> [TranscriptRole] {
        var roles: [TranscriptRole] = []
        roles.reserveCapacity(blocks.count)
        for (index, block) in blocks.enumerated() {
            let next = index + 1 < blocks.count ? blocks[index + 1] : nil
            roles.append(role(for: block, before: next))
        }
        return roles
    }

    static func role(for block: TranscriptBlock, before next: TranscriptBlock?) -> TranscriptRole {
        // Only the room's own lines take typographic roles. The echo is the
        // player's, and a refusal is already marked by its colour.
        guard block.kind == .narration else { return .body }
        let text = block.text
        if text.trimmingCharacters(in: .whitespaces).isEmpty { return .gap }
        if isRule(text) { return .rule }
        // A room name is underlined with plain dashes. The box-drawing rule
        // around a cutscene stands on its own and names nothing above it.
        if let next, next.kind == .narration, isUnderline(next.text) { return .title }
        let trimmed = text.trimmingCharacters(in: .whitespaces)
        if trimmed.count > 2, trimmed.hasPrefix("*"), trimmed.hasSuffix("*") {
            return .aside(String(trimmed.dropFirst().dropLast()))
        }
        return .body
    }

    /// Three or more of the same dash or box-drawing character, with nothing
    /// else on the line.
    static func isRule(_ text: String) -> Bool {
        isRun(of: "-", text) || isRun(of: "\u{2500}", text)
    }

    /// The plain-dash form only, which is what the turn core writes under a
    /// room name.
    static func isUnderline(_ text: String) -> Bool {
        isRun(of: "-", text)
    }

    private static func isRun(of character: Character, _ text: String) -> Bool {
        let trimmed = text.trimmingCharacters(in: .whitespaces)
        return trimmed.count >= 3 && trimmed.allSatisfy { $0 == character }
    }
}
