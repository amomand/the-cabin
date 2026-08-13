import Foundation

/// Frames over HTTP, from the resumable session API.
///
/// There is no socket to lose, so a locked phone costs nothing: the token is
/// still good when the app comes back. No `Origin` header is ever set —
/// `URLSession` adds none of its own, and the server admits a request without
/// one precisely so native clients are not locked out.
@MainActor
final class ServerTransport: GameTransport {
    /// Where the turn core is served from.
    ///
    /// Overridable for playtest builds pointed at a local uvicorn:
    /// `-CabinBaseURL http://127.0.0.1:8080` as a launch argument. Port 8080 is
    /// the API; 8000 is the static site, and pointing at it answers every
    /// request with a 404 no client can read.
    nonisolated static var defaultBaseURL: URL {
        if let override = UserDefaults.standard.string(forKey: "CabinBaseURL"),
           let url = URL(string: override) {
            return url
        }
        return URL(string: "https://the-cabin-api.fly.dev")!
    }

    private let baseURL: URL
    private let session: URLSession
    private let clientID: String?
    private let sleep: (UInt64) async throws -> Void
    private let now: () -> Date
    private var token: String?
    private var nextTurnID = 1

    var resumeHandle: String? {
        guard let token else { return nil }
        let state = ResumeState(token: token, nextTurnID: nextTurnID)
        guard let data = try? JSONEncoder().encode(state) else { return nil }
        return String(data: data, encoding: .utf8)
    }

    init(
        baseURL: URL = ServerTransport.defaultBaseURL,
        clientID: String?,
        session: URLSession? = nil,
        sleep: @escaping (UInt64) async throws -> Void = {
            try await Task.sleep(nanoseconds: $0)
        },
        now: @escaping () -> Date = Date.init
    ) {
        self.baseURL = baseURL
        self.clientID = clientID
        self.sleep = sleep
        self.now = now
        if let session {
            self.session = session
        } else {
            let config = URLSessionConfiguration.ephemeral
            // A turn is one model call; the server gives up at 20s. The wider
            // client budget includes a short retry without making the player
            // wait indefinitely for connectivity.
            config.timeoutIntervalForRequest = 45
            config.timeoutIntervalForResource = 45
            config.waitsForConnectivity = false
            self.session = URLSession(configuration: config)
        }
    }

    func adopt(resumeHandle: String) {
        if let data = resumeHandle.data(using: .utf8),
           let state = try? JSONDecoder().decode(ResumeState.self, from: data),
           state.nextTurnID > 0 {
            token = state.token
            nextTurnID = state.nextTurnID
        } else {
            // Handles written by the MVP were the bare token. Its server-side
            // session has never seen an idempotent turn, so its first id is 1.
            token = resumeHandle
            nextTurnID = 1
        }
    }

    func open() async throws -> RenderFrame {
        let body = try JSONEncoder().encode(CreateBody(clientID: clientID))
        let request = post("/session", body: body, token: nil)
        let created: SessionCreation = try await performWithRetry(
            request,
            repeatable: clientID != nil
        )
        token = created.token
        nextTurnID = 1
        return created.frame
    }

    func send(_ turn: PlayerTurn) async throws -> RenderFrame {
        guard let token else {
            throw TransportFailure.lost(Narration.threadGoneCold)
        }
        let turnID = nextTurnID
        let body = try JSONEncoder().encode(TurnBody(turn, turnID: turnID))
        let request = post("/session/turn", body: body, token: token)
        let frame: RenderFrame = try await performWithRetry(request, repeatable: true)
        nextTurnID = turnID + 1
        if frame.gameOver {
            // The server releases the session on game over, so the handle is
            // spent. Dropping it here keeps a stale token out of persistence.
            self.token = nil
            nextTurnID = 1
        }
        return frame
    }

    func probe() async throws {
        // An empty command is not a turn: the session returns a bare prompt
        // frame without reaching the interpreter, so this costs no model call
        // and moves nothing. It is only safe while the run wants input; a run
        // waiting on a keypress would read this as the keypress.
        _ = try await send(.input(""))
    }

    // MARK: - Requests

    private func post(_ path: String, body: Data, token: String?) -> URLRequest {
        var request = URLRequest(url: baseURL.appendingPathComponent(path))
        request.httpMethod = "POST"
        request.httpBody = body
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        if let token {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        return request
    }

    private func perform<T: Decodable>(_ request: URLRequest) async throws -> T {
        let data: Data
        let response: URLResponse
        do {
            (data, response) = try await session.data(for: request)
        } catch is CancellationError {
            throw CancellationError()
        } catch let error as URLError where error.code == .cancelled {
            // An abandoned wait is not a failed one. Narrating it would have
            // the room fall silent over something the player never did.
            throw CancellationError()
        } catch let error as URLError {
            throw NetworkFailure(
                definitelyUnsent: Self.definitelyUnsent.contains(error.code)
            )
        } catch {
            // URLSession normally wraps transport failures in URLError. Treat
            // an unknown one conservatively: the request may have reached the
            // server, so only an idempotent operation may repeat it.
            throw NetworkFailure(definitelyUnsent: false)
        }

        guard let http = response as? HTTPURLResponse else {
            throw TransportFailure.malformed
        }

        guard http.statusCode == 200 else {
            throw failure(status: http.statusCode, body: data)
        }

        do {
            return try JSONDecoder().decode(T.self, from: data)
        } catch {
            throw TransportFailure.malformed
        }
    }

    private func performWithRetry<T: Decodable>(
        _ original: URLRequest,
        repeatable: Bool
    ) async throws -> T {
        let deadline = now().addingTimeInterval(Self.retryBudget)
        var attempt = 1
        var request = original

        while true {
            request.timeoutInterval = max(1, deadline.timeIntervalSince(now()))
            do {
                return try await perform(request)
            } catch is CancellationError {
                throw CancellationError()
            } catch let network as NetworkFailure {
                let canRepeat = network.definitelyUnsent || repeatable
                guard canRepeat,
                      attempt < Self.maxAttempts,
                      try await waitBeforeRetry(Self.shortDelay, deadline: deadline)
                else {
                    throw TransportFailure.unreachable
                }
            } catch let failure as TransportFailure {
                let delay: UInt64
                switch failure {
                case .busy:
                    delay = Self.shortDelay
                case .rateLimited:
                    delay = Self.rateLimitDelay
                case .malformed where repeatable:
                    delay = Self.shortDelay
                default:
                    throw failure
                }
                guard attempt < Self.maxAttempts,
                      try await waitBeforeRetry(delay, deadline: deadline)
                else {
                    throw failure
                }
            }
            attempt += 1
        }
    }

    private func waitBeforeRetry(_ nanoseconds: UInt64, deadline: Date) async throws -> Bool {
        let seconds = TimeInterval(nanoseconds) / 1_000_000_000
        guard now().addingTimeInterval(seconds) < deadline else { return false }
        try await sleep(nanoseconds)
        return now() < deadline
    }

    /// Map a refusal onto what the player can do about it, carrying the
    /// server's own narration rather than inventing any.
    private func failure(status: Int, body: Data) -> TransportFailure {
        guard let narrated = try? JSONDecoder().decode(NarratedFailure.self, from: body) else {
            return .malformed
        }
        switch status {
        case 404, 500:
            token = nil
            nextTurnID = 1
            return .lost(narrated.message)
        case 409:
            return .busy(narrated.message)
        case 429:
            return .rateLimited(narrated.message)
        default:
            return .narrated(narrated.message)
        }
    }

    // MARK: - Bodies

    private struct CreateBody: Encodable {
        let clientID: String?

        enum CodingKeys: String, CodingKey {
            case clientID = "client_id"
        }
    }

    private struct TurnBody: Encodable {
        let type: String
        let text: String?
        let turnID: Int

        enum CodingKeys: String, CodingKey {
            case type
            case text
            case turnID = "turn_id"
        }

        init(_ turn: PlayerTurn, turnID: Int) {
            self.turnID = turnID
            switch turn {
            case .keypress:
                type = "keypress"
                text = nil
            case .input(let text):
                self.type = "input"
                self.text = text
            }
        }
    }

    private struct ResumeState: Codable {
        let token: String
        let nextTurnID: Int
    }

    private struct NetworkFailure: Error {
        let definitelyUnsent: Bool
    }

    private static let maxAttempts = 3
    private static let retryBudget: TimeInterval = 45
    private static let shortDelay: UInt64 = 250_000_000
    private static let rateLimitDelay: UInt64 = 1_000_000_000
    private static let definitelyUnsent: Set<URLError.Code> = [
        .cannotFindHost,
        .cannotConnectToHost,
        .dnsLookupFailed,
        .notConnectedToInternet,
        .internationalRoamingOff,
        .callIsActive,
        .dataNotAllowed,
    ]
}
