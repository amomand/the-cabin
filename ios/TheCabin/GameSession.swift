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
    /// A presentation-only opener over a restored run. Removing it never
    /// advances the run beneath it.
    @Published private(set) var launchOpenerLines: [String]?

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
    private var hasStarted = false
    private var pendingTurn: PlayerTurn?
    private var cachedOpenerLines: [String]?
    private var isAtRunOpener = false

    init(
        transport: GameTransport,
        store: TranscriptStore = TranscriptStore(),
        now: @escaping () -> Date = Date.init
    ) {
        self.transport = transport
        self.store = store
        self.now = now
    }

    /// Put the run back from disk. No network, so it is intact beneath the
    /// cold-launch opener before the first request is even sent.
    func restore() {
        guard let run = store.load() else { return }
        blocks = run.blocks
        status = run.status
        mode = run.mode
        prompt = run.prompt
        pendingTurn = run.pendingTurn
        cachedOpenerLines = run.openerLines
        isAtRunOpener = run.isAtRunOpener ?? Self.looksLikeLegacyRunOpener(run)
        if pendingTurn != nil {
            // No second command is accepted until the request whose answer may
            // have been lost is replayed. A tap retries it unchanged.
            mode = .keypress
            prompt = nil
        }
        isHoldingRestoredEnding = run.resumeHandle == nil && run.mode == .ended
        if let handle = run.resumeHandle {
            transport.adopt(resumeHandle: handle)
        }
        if !isAtRunOpener {
            // The saved run stays intact beneath this cover. Newer runs replay
            // the exact lines their transport supplied; pre-change runs use a
            // fallback held to the Python canon by an executable parity test.
            if let cachedOpenerLines, !cachedOpenerLines.isEmpty {
                launchOpenerLines = cachedOpenerLines
            } else {
                launchOpenerLines = LaunchOpener.legacyFallbackLines
            }
        }
    }

    /// Reveal the restored run without sending anything to it.
    func dismissLaunchOpener() {
        launchOpenerLines = nil
    }

    /// Open a run, or confirm the restored one is still there.
    func start() async {
        // From here on, foreground callbacks may check the run. Before this,
        // `.active` can race ahead of the launch task and must leave the initial
        // probe to `start()`.
        hasStarted = true
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
        guard hasStarted, transport.resumeHandle != nil else { return }
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
        guard launchOpenerLines == nil else { return }
        let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard mode == .input, !isWorking, !trimmed.isEmpty else { return }
        append(.init(kind: .echo, text: (prompt ?? "> ") + trimmed))
        await advance(.input(trimmed))
    }

    /// Acknowledge a frame that is waiting for any key, or begin again once the
    /// run has ended.
    func acknowledge() async {
        guard launchOpenerLines == nil, !isWorking else { return }
        switch mode {
        case .keypress:
            await advance(pendingTurn ?? .keypress)
        case .ended:
            await begin()
        case .input:
            break
        }
    }

    // MARK: - Turns

    private func begin() async {
        isHoldingRestoredEnding = false
        isAtRunOpener = false
        // A new run has no readings yet. Without this the intro of the next run
        // would carry the last one's health and fear, since an intro frame has
        // no status line of its own to overwrite them.
        status = nil
        // If opening fails, a tap should retry the open directly. Leaving the
        // initial keypress mode here would try to advance a run that has no
        // resume handle, narrate it as lost, and make recovery take two taps.
        mode = .ended
        await open()
    }

    private func confirmAlive() async {
        // Only an input frame can be probed: a run waiting on a keypress would
        // read the probe as the keypress and move on without the player.
        guard mode == .input, !isWorking else { return }
        pendingTurn = .input("")
        persist()
        isWorking = true
        defer { isWorking = false }
        do {
            try await transport.probe()
            pendingTurn = nil
            lastContact = now()
        } catch is CancellationError {
            // The wait was abandoned, not refused. Nothing to narrate.
            mode = .keypress
            prompt = nil
        } catch let failure as TransportFailure {
            handleTurnFailure(failure)
        } catch {
            handleTurnFailure(.malformed)
        }
        persist()
    }

    private func open() async {
        isWorking = true
        defer { isWorking = false }
        do {
            apply(try await transport.open(), asRunOpener: true)
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

    private func advance(_ turn: PlayerTurn) async {
        if pendingTurn == nil {
            pendingTurn = turn
            // Persist before the request leaves. Even a force-quit in the
            // ambiguous window can then replay the same logical turn.
            persist()
        }

        isWorking = true
        defer { isWorking = false }
        do {
            let frame = try await transport.send(turn)
            pendingTurn = nil
            apply(frame)
            lastContact = now()
        } catch is CancellationError {
            // The request may have landed. Keep it behind the tap cursor so a
            // relaunch or explicit retry sends the same turn id and body.
            mode = .keypress
            prompt = nil
        } catch let failure as TransportFailure {
            handleTurnFailure(failure)
        } catch {
            handleTurnFailure(.malformed)
        }
        persist()
    }

    private func handleTurnFailure(_ failure: TransportFailure) {
        handle(failure)
        switch failure {
        case .lost, .narrated:
            pendingTurn = nil
        case .busy, .rateLimited, .unreachable, .malformed:
            mode = .keypress
            prompt = nil
        }
    }

    private func apply(_ frame: RenderFrame, asRunOpener: Bool = false) {
        if asRunOpener {
            isAtRunOpener = frame.mode == .keypress
            if isAtRunOpener, !frame.lines.isEmpty {
                cachedOpenerLines = frame.lines
            }
        } else {
            isAtRunOpener = false
        }
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
                prompt: prompt,
                pendingTurn: pendingTurn,
                openerLines: cachedOpenerLines,
                isAtRunOpener: isAtRunOpener
            )
        )
    }

    /// A run file from before `isAtRunOpener` existed can still be recognised
    /// without advancing it. The pending-keypress form covers an opener whose
    /// dismissal was attempted but whose answer was lost.
    private static func looksLikeLegacyRunOpener(_ run: PersistedRun) -> Bool {
        guard run.mode == .keypress, run.prompt == nil else { return false }
        let visible = run.blocks.map(\.text)
        let canonical = LaunchOpener.legacyFallbackLines
        guard visible.starts(with: canonical) else { return false }
        return visible.count == canonical.count || run.pendingTurn == .keypress
    }
}
