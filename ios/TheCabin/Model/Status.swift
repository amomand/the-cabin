import Foundation

/// The player's health and fear, pinned outside the transcript.
///
/// There is no structured channel for these: the turn core appends a single
/// formatted line to every room render, and the browser client scrapes it the
/// same way. Parsing here keeps the line out of the transcript so it does not
/// scroll away with the prose.
struct Status: Equatable, Codable {
    var health: Int
    var fear: Int

    /// Parse the status line, or return nil for any line that is not one.
    ///
    /// A line that fails to parse is left in the transcript untouched, so a
    /// change of format upstream loses formatting rather than text.
    init?(statusLine line: String) {
        let fields = line.split(whereSeparator: { $0.isWhitespace })
        guard fields.count == 4,
              fields[0] == "Health:",
              fields[2] == "Fear:",
              let health = Int(fields[1]),
              let fear = Int(fields[3])
        else { return nil }
        self.health = health
        self.fear = fear
    }
}
