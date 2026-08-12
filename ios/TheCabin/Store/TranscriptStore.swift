import Foundation

/// One block of the transcript.
struct TranscriptBlock: Codable, Equatable, Identifiable {
    enum Kind: String, Codable {
        /// A line from the turn core.
        case narration
        /// The player's own words, echoed back under the prompt they were typed at.
        case echo
        /// A refusal, narrated.
        case refusal
    }

    var id: UUID = UUID()
    var kind: Kind
    var text: String
}

/// Everything needed to put the screen back as the player left it.
struct PersistedRun: Codable, Equatable {
    var resumeHandle: String?
    var blocks: [TranscriptBlock]
    var status: Status?
    var mode: RenderFrame.Mode
    var prompt: String?

    static let empty = PersistedRun(
        resumeHandle: nil,
        blocks: [],
        status: nil,
        mode: .keypress,
        prompt: nil
    )
}

/// The transcript on disk.
///
/// Written after every frame so a kill from the app switcher loses nothing, and
/// read before any network call so a relaunch shows the run immediately rather
/// than an empty screen waiting on a request.
struct TranscriptStore {
    private let fileURL: URL

    init(directory: URL? = nil) {
        let base = directory ?? FileManager.default.urls(
            for: .applicationSupportDirectory,
            in: .userDomainMask
        )[0]
        try? FileManager.default.createDirectory(at: base, withIntermediateDirectories: true)
        fileURL = base.appendingPathComponent("run.json")
    }

    func load() -> PersistedRun? {
        guard let data = try? Data(contentsOf: fileURL) else { return nil }
        return try? JSONDecoder().decode(PersistedRun.self, from: data)
    }

    /// Persist the run, atomically so a crash mid-write cannot leave a
    /// half-file that fails to decode on the next launch.
    func save(_ run: PersistedRun) {
        guard let data = try? JSONEncoder().encode(run) else { return }
        try? data.write(to: fileURL, options: .atomic)
    }

    func clear() {
        try? FileManager.default.removeItem(at: fileURL)
    }
}
