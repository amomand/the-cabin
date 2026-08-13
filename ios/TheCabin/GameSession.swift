import Foundation

/// The run, as the screen sees it.
///
/// Holds the transcript, the status line, and what the game is currently asking
/// for. It knows nothing about HTTP: frames arrive from whatever `GameTransport`
/// it was handed.
@MainActor
final class GameSession: ObservableObject {
    @Published private(set) var blocks: [TranscriptBlock] = []
    @Published private(set) var status: Status?
    @Published private(set) var mode: RenderFrame.Mode = .keypress
    @Published private(set) var prompt: String?
    @Published private(set) var isWorking = false

    /// Long playtests would otherwise grow the transcript, and the file it is
    /// written to, without limit. Older blocks scroll out of reach long before
    /// this.
    private static let maxBlocks = 2000

    /// A run cannot go cold in the time it takes to switch apps, so a check
    /// this soon after the last one would only spend rate limit.
    private static let confirmationGrace: TimeInterval = 30

    private let transport: GameTransport
    private let store: TranscriptStore
    private let now: () -> Date
    private var lastContact: Date?
    private var isHoldingRestoredEnding = false

    init(
        transport: GameTransport,
        store: TranscriptStore = TranscriptStore(),
        now: @escaping () -> Date = Date.init
    ) {
        self.transport = transport
        self.store = store
        self.now = now
    }

    /// Put the screen back from disk. No network, so the run is on screen
    /// before the first request is even sent.
    func restore() {
        guard let run = store.load() else { return }
        blocks = run.blocks
        status = run.status
        mode = run.mode
        prompt = run.prompt
        isHoldingRestoredEnding = run.resumeHandle == nil && run.mode == .ended
        if let handle = run.resumeHandle {
            transport.adopt(resumeHandle: handle)
        }
    }

    /// Open a run, or confirm the restored one is still there.
    func start() async {
        if transport.resumeHandle == nil {
            // An ending restored from disk stays on screen just as it did before
            // the relaunch. The player's next tap, not app startup, begins again.
            guard !isHoldingRestoredEnding else { return }
            await begin()
        } else {
            await confirmAlive()
        }
    }

    /// Called when the app comes back to the foreground.
    ///
    /// A locked phone costs the run nothing, but a long enough absence expires
    /// it server-side, and the player should find that out now rather than by
    /// typing into a thread that is already cold.
    func resumeFromBackground() async {
        guard transport.resumeHandle != nil else { return }
        // A cold launch reaches the foreground and runs `start()` in the same
        // breath, so without this the app would check twice before the player
        // had touched anything.
        if let lastContact, now().timeIntervalSince(lastContact) < Self.confirmationGrace {
            return
        }
        await confirmAlive()
    }

    /// Send a command.
    func submit(_ text: String) async {
        let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard mode == .input, !isWorking, !trimmed.isEmpty else { return }
        append(.init(kind: .echo, text: (prompt ?? "> ") + trimmed))
        await advance { try await self.transport.send(.input(trimmed)) }
    }

    /// Acknowledge a frame that is waiting for any key, or begin again once the
    /// run has ended.
    func acknowledge() async {
        guard !isWorking else { return }
        switch mode {
        case .keypress:
            await advance { try await self.transport.send(.keypress) }
        case .ended:
            await begin()
        case .input:
            break
        }
    }

    // MARK: - Turns

    private func begin() async {
        isHoldingRestoredEnding = false
        // A new run has no readings yet. Without this the intro of the next run
        // would carry the last one's health and fear, since an intro frame has
        // no status line of its own to overwrite them.
        status = nil
        // If opening fails, a tap should retry the open directly. Leaving the
        // initial keypress mode here would try to advance a run that has no
        // resume handle, narrate it as lost, and make recovery take two taps.
        mode = .ended
        await advance { try await self.transport.open() }
    }

    private func confirmAlive() async {
        // Only an input frame can be probed: a run waiting on a keypress would
        // read the probe as the keypress and move on without the player.
        guard mode == .input, !isWorking else { return }
        isWorking = true
        defer { isWorking = false }
        do {
            try await transport.probe()
            lastContact = now()
        } catch is CancellationError {
            // The wait was abandoned, not refused. Nothing to narrate.
        } catch let failure as TransportFailure {
            handle(failure)
        } catch {
            handle(.malformed)
        }
        persist()
    }

    private func advance(_ turn: @escaping () async throws -> RenderFrame) async {
        isWorking = true
        defer { isWorking = false }
        do {
            apply(try await turn())
            lastContact = now()
        } catch is CancellationError {
            // The wait was abandoned, not refused. Nothing to narrate.
        } catch let failure as TransportFailure {
            handle(failure)
        } catch {
            handle(.malformed)
        }
        persist()
    }

    private func apply(_ frame: RenderFrame) {
        var updatedBlocks = frame.clear ? [] : blocks
        for line in frame.lines {
            // The status line is pinned above the transcript instead of
            // scrolling away with the prose that came with it.
            if let parsed = Status(statusLine: line) {
                status = parsed
            } else {
                updatedBlocks.append(.init(kind: .narration, text: line))
            }
        }
        if updatedBlocks.count > Self.maxBlocks {
            updatedBlocks.removeFirst(updatedBlocks.count - Self.maxBlocks)
        }
        // One frame is one visible update, even when it carries many lines.
        blocks = updatedBlocks
        mode = frame.mode
        prompt = frame.prompt
    }

    private func handle(_ failure: TransportFailure) {
        append(.init(kind: .refusal, text: failure.narration))
        guard case .lost = failure else { return }
        // The run cannot be continued, so hold here rather than restarting
        // under the player: the intro frame clears the screen, and opening one
        // now would wipe the line they are still reading. The next tap opens a
        // fresh run, whose authored intro reads as the restart, and durable
        // saves outlive the session, so `load` works from there.
        status = nil
        mode = .ended
    }

    // MARK: - Transcript

    private func append(_ block: TranscriptBlock) {
        blocks.append(block)
        if blocks.count > Self.maxBlocks {
            blocks.removeFirst(blocks.count - Self.maxBlocks)
        }
    }

    private func persist() {
        store.save(
            PersistedRun(
                resumeHandle: transport.resumeHandle,
                blocks: blocks,
                status: status,
                mode: mode,
                prompt: prompt
            )
        )
    }
}
