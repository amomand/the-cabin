import Foundation

/// The local playtest notebook and its deterministic Markdown export.
///
/// The archive is deliberately separate from `run.json`: it contains only the
/// note DTO, never a resume handle or anything from the keychain. Each append
/// is a locked read-modify-write followed by an atomic replacement.
final class PlaytestNoteStore {
    static let archiveFilename = "playtest-notes.json"
    static let exportFilename = "The Cabin playtest notes.md"

    private static let schemaVersion = 1

    private struct Archive: Codable {
        let schemaVersion: Int
        var notes: [PlaytestNote]
    }

    private enum ArchiveState {
        case missing
        case valid([PlaytestNote])
        case invalid
    }

    private let directory: URL
    private let archiveURL: URL
    private let exportURL: URL
    /// Every store in the process targets the same app-support notebook by
    /// default. The lock therefore belongs to the file boundary, not one
    /// wrapper instance; otherwise two wrappers can atomically replace each
    /// other's freshly appended page.
    private static let archiveLock = NSLock()

    init(directory: URL? = nil) {
        let base = directory ?? FileManager.default.urls(
            for: .applicationSupportDirectory,
            in: .userDomainMask
        )[0]
        self.directory = base
        archiveURL = base.appendingPathComponent(Self.archiveFilename)
        exportURL = base.appendingPathComponent(Self.exportFilename)
        try? FileManager.default.createDirectory(at: base, withIntermediateDirectories: true)
    }

    func load() -> [PlaytestNote] {
        withLock {
            guard case .valid(let notes) = readArchive() else { return [] }
            return notes
        }
    }

    /// Append without ever replacing an unreadable archive. A damaged notebook
    /// remains recoverable instead of being silently overwritten by one page.
    @discardableResult
    func append(_ note: PlaytestNote) -> Bool {
        withLock {
            let notes: [PlaytestNote]
            switch readArchive() {
            case .missing:
                notes = []
            case .valid(let existing):
                notes = existing
            case .invalid:
                return false
            }

            let archive = Archive(
                schemaVersion: Self.schemaVersion,
                notes: notes + [note]
            )
            guard let data = try? Self.encoder.encode(archive) else { return false }
            do {
                try FileManager.default.createDirectory(
                    at: directory,
                    withIntermediateDirectories: true
                )
                try data.write(to: archiveURL, options: .atomic)
                return true
            } catch {
                return false
            }
        }
    }

    /// Rewrite one stable local file for `ShareLink` to hand to Files or
    /// AirDrop. No share target is contacted until the player chooses one.
    func prepareMarkdownExport() -> URL? {
        withLock {
            guard case .valid(let notes) = readArchive(), !notes.isEmpty else {
                return nil
            }
            let data = Data(Self.markdown(notes: notes).utf8)
            do {
                try data.write(to: exportURL, options: .atomic)
                return exportURL
            } catch {
                return nil
            }
        }
    }

    static func markdown(notes: [PlaytestNote]) -> String {
        var lines = ["# The Cabin playtest notes", ""]
        for (offset, note) in notes.enumerated() {
            let context = note.context
            lines.append("## Note \(offset + 1)")
            lines.append("")
            lines.append("- Captured: `\(timestamp(context.capturedAt))`")
            lines.append("- Successful turn: \(context.successfulTurnIndex)")
            if let status = context.status {
                lines.append("- Health: \(status.health)")
                lines.append("- Fear: \(status.fear)")
            }
            if let story = context.story {
                if let act = story.act { lines.append("- Act: \(oneLine(act))") }
                if let location = story.location {
                    lines.append("- Location: \(oneLine(location))")
                }
                if let layer = story.worldLayer {
                    lines.append("- World layer: \(oneLine(layer))")
                }
                if !story.markers.isEmpty {
                    lines.append("- Story markers: \(story.markers.map(oneLine).joined(separator: ", "))")
                }
            }

            lines.append("")
            lines.append("### Recent transcript")
            lines.append("")
            if context.recentTranscript.isEmpty {
                lines.append("- None.")
            } else {
                for line in context.recentTranscript {
                    lines.append("- `\(line.kind.rawValue)`: \(oneLine(line.text))")
                }
            }

            lines.append("")
            lines.append("### Observation")
            lines.append("")
            lines.append(note.body)
            lines.append("")
        }
        return lines.joined(separator: "\n") + "\n"
    }

    private func readArchive() -> ArchiveState {
        guard FileManager.default.fileExists(atPath: archiveURL.path) else {
            return .missing
        }
        guard let data = try? Data(contentsOf: archiveURL),
              let archive = try? Self.decoder.decode(Archive.self, from: data),
              archive.schemaVersion == Self.schemaVersion
        else { return .invalid }
        return .valid(archive.notes)
    }

    private func withLock<T>(_ operation: () -> T) -> T {
        Self.archiveLock.lock()
        defer { Self.archiveLock.unlock() }
        return operation()
    }

    private static let encoder: JSONEncoder = {
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.sortedKeys]
        return encoder
    }()

    private static let decoder = JSONDecoder()

    private static func timestamp(_ date: Date) -> String {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        formatter.timeZone = TimeZone(secondsFromGMT: 0)
        return formatter.string(from: date)
    }

    private static func oneLine(_ text: String) -> String {
        text.replacingOccurrences(of: "\r\n", with: "\n")
            .replacingOccurrences(of: "\r", with: "\n")
            .replacingOccurrences(of: "\n", with: " ↵ ")
    }
}
