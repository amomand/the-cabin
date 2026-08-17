import Foundation
@testable import TheCabin

/// A transport that answers from a script, so session behaviour can be tested
/// without a server or a model call.
@MainActor
final class StubTransport: GameTransport {
    var resumeHandle: String?

    var openResults: [Result<RenderFrame, TransportFailure>] = []
    var sendResults: [Result<RenderFrame, TransportFailure>] = []
    var probeResults: [Result<Void, TransportFailure>] = []
    /// Set to have the next turn abandon its wait rather than fail.
    var cancelNextSend = false
    /// Set to have the next liveness check abandon its wait rather than fail.
    var cancelNextProbe = false

    private(set) var opens = 0
    private(set) var probes = 0
    private(set) var sent: [PlayerTurn] = []

    func adopt(resumeHandle: String) {
        self.resumeHandle = resumeHandle
    }

    func open() async throws -> RenderFrame {
        opens += 1
        guard !openResults.isEmpty else { throw TransportFailure.unreachable }
        switch openResults.removeFirst() {
        case .success(let frame):
            resumeHandle = "token-\(opens)"
            return frame
        case .failure(let failure):
            throw failure
        }
    }

    func send(_ turn: PlayerTurn) async throws -> RenderFrame {
        sent.append(turn)
        if cancelNextSend {
            cancelNextSend = false
            throw CancellationError()
        }
        guard !sendResults.isEmpty else { throw TransportFailure.unreachable }
        switch sendResults.removeFirst() {
        case .success(let frame):
            if frame.gameOver { resumeHandle = nil }
            return frame
        case .failure(let failure):
            if case .lost = failure { resumeHandle = nil }
            throw failure
        }
    }

    func probe() async throws {
        probes += 1
        if cancelNextProbe {
            cancelNextProbe = false
            throw CancellationError()
        }
        guard !probeResults.isEmpty else { return }
        switch probeResults.removeFirst() {
        case .success:
            return
        case .failure(let failure):
            if case .lost = failure { resumeHandle = nil }
            throw failure
        }
    }
}
