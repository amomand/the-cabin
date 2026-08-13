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
    private var token: String?

    var resumeHandle: String? { token }

    init(
        baseURL: URL = ServerTransport.defaultBaseURL,
        clientID: String?,
        session: URLSession? = nil
    ) {
        self.baseURL = baseURL
        self.clientID = clientID
        if let session {
            self.session = session
        } else {
            let config = URLSessionConfiguration.ephemeral
            // A turn is one model call; the server gives up at 20s.
            config.timeoutIntervalForRequest = 45
            config.waitsForConnectivity = false
            self.session = URLSession(configuration: config)
        }
    }

    func adopt(resumeHandle: String) {
        token = resumeHandle
    }

    func open() async throws -> RenderFrame {
        let body = try JSONEncoder().encode(CreateBody(clientID: clientID))
        let request = post("/session", body: body, token: nil)
        let created: SessionCreation = try await perform(request)
        token = created.token
        return created.frame
    }

    func send(_ turn: PlayerTurn) async throws -> RenderFrame {
        guard let token else {
            throw TransportFailure.lost(Narration.threadGoneCold)
        }
        let body = try JSONEncoder().encode(TurnBody(turn))
        let request = post("/session/turn", body: body, token: token)
        let frame: RenderFrame = try await perform(request)
        if frame.gameOver {
            // The server releases the session on game over, so the handle is
            // spent. Dropping it here keeps a stale token out of persistence.
            self.token = nil
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
        } catch {
            throw TransportFailure.unreachable
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

    /// Map a refusal onto what the player can do about it, carrying the
    /// server's own narration rather than inventing any.
    private func failure(status: Int, body: Data) -> TransportFailure {
        guard let narrated = try? JSONDecoder().decode(NarratedFailure.self, from: body) else {
            return .malformed
        }
        switch status {
        case 404, 500:
            token = nil
            return .lost(narrated.message)
        case 409, 429:
            return .busy(narrated.message)
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

        init(_ turn: PlayerTurn) {
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
}
