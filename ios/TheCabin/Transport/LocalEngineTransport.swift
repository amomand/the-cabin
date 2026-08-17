import Foundation

protocol PythonDispatching: AnyObject {
    func dispatch(_ request: Data) async throws -> Data
}

final class EmbeddedPythonDispatcher: PythonDispatching {
    func dispatch(_ request: Data) async throws -> Data {
        guard let requestString = String(data: request, encoding: .utf8) else {
            throw TransportFailure.malformed
        }
        return try await withCheckedThrowingContinuation { continuation in
            PythonBridge.shared().performRequest(requestString) { response, error in
                if let error {
                    continuation.resume(throwing: error)
                } else if let response, let data = response.data(using: .utf8) {
                    continuation.resume(returning: data)
                } else {
                    continuation.resume(throwing: TransportFailure.malformed)
                }
            }
        }
    }
}

/// The native transport for the embedded WebGameSession turn core.
///
/// Swift owns opaque handles and frame mapping only. Story state, save/load,
/// overlays, endings, and idempotent turn decisions remain in Python.
@MainActor
final class LocalEngineTransport: GameTransport {
    private let dispatcher: PythonDispatching
    private var handle: String?
    private var adopted = false
    private var nextTurnID = 1

    var resumeHandle: String? { handle }
    var probeCreatesTurn: Bool { false }

    init(dispatcher: PythonDispatching = EmbeddedPythonDispatcher()) {
        self.dispatcher = dispatcher
    }

    func adopt(resumeHandle: String) {
        handle = resumeHandle
        adopted = false
        if let data = resumeHandle.data(using: .utf8),
           let state = try? JSONDecoder().decode(ResumeState.self, from: data),
           state.version == 1,
           state.nextTurnID > 0 {
            nextTurnID = state.nextTurnID
        } else {
            nextTurnID = 1
        }
    }

    func open() async throws -> RenderFrame {
        let response = try await perform(Request(operation: "open"))
        guard let frame = response.frame else { throw TransportFailure.malformed }
        try accept(response)
        adopted = true
        return frame
    }

    func send(_ turn: PlayerTurn) async throws -> RenderFrame {
        try await ensureAdopted()
        guard handle != nil else {
            throw TransportFailure.lost(Narration.threadGoneCold)
        }
        let turnID = nextTurnID
        let response = try await perform(
            Request(operation: "send", turnID: turnID, turn: turn)
        )
        try accept(response)
        guard let frame = response.frame else { throw TransportFailure.malformed }
        if frame.gameOver {
            handle = nil
            nextTurnID = 1
        }
        return frame
    }

    func probe() async throws {
        try await ensureAdopted()
        guard handle != nil else {
            throw TransportFailure.lost(Narration.threadGoneCold)
        }
        _ = try await perform(Request(operation: "probe"))
    }

    func persist() async {
        guard handle != nil else { return }
        do {
            try await ensureAdopted()
            // Preserve Swift's logical turn id. If Python completed a turn in
            // the force-quit window, the pending Swift turn must still replay
            // the older id and receive Python's already-durable frame.
            _ = try await perform(Request(operation: "persist"))
        } catch {
            // The last completed frame already forced a checkpoint. Lifecycle
            // persistence is best-effort and must not invent player-facing text.
        }
    }

    private func ensureAdopted() async throws {
        guard !adopted, let handle else { return }
        let response = try await perform(
            Request(operation: "adopt", resumeHandle: handle)
        )
        guard response.resumeHandle != nil else { throw TransportFailure.malformed }
        // Do not advance nextTurnID here. A stale Swift handle plus a newer
        // Python checkpoint is the expected ambiguous-response replay window.
        adopted = true
    }

    private func perform(_ request: Request) async throws -> Response {
        let data = try JSONEncoder().encode(request)
        let responseData: Data
        do {
            responseData = try await dispatcher.dispatch(data)
        } catch is CancellationError {
            throw CancellationError()
        } catch let failure as TransportFailure {
            throw failure
        } catch {
            throw TransportFailure.unreachable
        }
        guard let response = try? JSONDecoder().decode(Response.self, from: responseData) else {
            throw TransportFailure.malformed
        }
        guard response.ok else {
            switch response.kind {
            case "lost", "mismatch":
                handle = nil
                nextTurnID = 1
                throw TransportFailure.lost(Narration.threadGoneCold)
            default:
                throw TransportFailure.malformed
            }
        }
        return response
    }

    private func accept(_ response: Response) throws {
        guard let handle = response.resumeHandle,
              let data = handle.data(using: .utf8),
              let state = try? JSONDecoder().decode(ResumeState.self, from: data),
              state.version == 1,
              state.nextTurnID > 0
        else {
            throw TransportFailure.malformed
        }
        self.handle = handle
        nextTurnID = state.nextTurnID
    }

    private struct Request: Encodable {
        let operation: String
        var resumeHandle: String?
        var turnID: Int?
        var turn: PlayerTurn?

        enum CodingKeys: String, CodingKey {
            case operation
            case resumeHandle = "resume_handle"
            case turnID = "turn_id"
            case turn
        }

        init(
            operation: String,
            resumeHandle: String? = nil,
            turnID: Int? = nil,
            turn: PlayerTurn? = nil
        ) {
            self.operation = operation
            self.resumeHandle = resumeHandle
            self.turnID = turnID
            self.turn = turn
        }
    }

    private struct Response: Decodable {
        let ok: Bool
        let frame: RenderFrame?
        let resumeHandle: String?
        let kind: String?

        enum CodingKeys: String, CodingKey {
            case ok
            case frame
            case resumeHandle = "resume_handle"
            case kind
        }
    }

    private struct ResumeState: Decodable {
        let version: Int
        let nextTurnID: Int

        enum CodingKeys: String, CodingKey {
            case version
            case nextTurnID = "next_turn_id"
        }
    }
}
