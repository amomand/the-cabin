import Foundation

/// One turn's worth of player intent.
enum PlayerTurn: Codable, Equatable {
    /// Acknowledge a frame that is waiting for any key.
    case keypress
    /// Send a command.
    case input(String)

    private enum CodingKeys: String, CodingKey {
        case type
        case text
    }

    private enum Kind: String, Codable {
        case keypress
        case input
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        switch try container.decode(Kind.self, forKey: .type) {
        case .keypress:
            self = .keypress
        case .input:
            self = .input(try container.decode(String.self, forKey: .text))
        }
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)
        switch self {
        case .keypress:
            try container.encode(Kind.keypress, forKey: .type)
        case .input(let text):
            try container.encode(Kind.input, forKey: .type)
            try container.encode(text, forKey: .text)
        }
    }
}

/// Why a turn could not be delivered.
enum TransportFailure: Error, Equatable {
    /// The other end narrated a refusal. Its words are already in the world's
    /// voice, so they are rendered verbatim.
    case narrated(String)
    /// The run is gone and cannot be continued: an expired or unknown token, or
    /// a turn that died mid-flight. Carries the narrated line that came with it.
    case lost(String)
    /// Refused for now, and worth trying again unchanged.
    case busy(String)
    /// Rate limited for now. Retrying needs the longer backoff reserved for
    /// server capacity rather than the short wait used for an in-flight turn.
    case rateLimited(String)
    /// Nothing answered: no network, or the host is unreachable.
    case unreachable
    /// Something answered in a shape this client cannot read.
    case malformed
}

/// Where frames come from.
///
/// The UI holds one of these and never learns whether the turn core is across
/// the network or in the same process. `resumeHandle` is deliberately opaque:
/// the server transport keeps a session token there, an on-device engine would
/// keep a save slot, and the persistence layer stores whatever it is given
/// without inspecting it.
@MainActor
protocol GameTransport: AnyObject {
    /// An opaque handle that can continue this run after a relaunch, or nil
    /// when there is no run to continue.
    var resumeHandle: String? { get }

    /// Whether `probe()` is itself an idempotent turn that must survive an
    /// ambiguous app kill. The HTTP surface sends an empty input; the local
    /// engine validates its checkpoint without advancing anything.
    var probeCreatesTurn: Bool { get }

    /// Continue a run persisted from an earlier launch.
    func adopt(resumeHandle: String)

    /// Begin a new run and return its first frame.
    func open() async throws -> RenderFrame

    /// Advance the run by one turn.
    func send(_ turn: PlayerTurn) async throws -> RenderFrame

    /// Check the run is still there, without advancing it.
    ///
    /// Throws `.lost` if it is gone. Only safe to call while the last frame was
    /// asking for input: a run waiting on a keypress cannot be probed without
    /// consuming the keypress.
    func probe() async throws

    /// Flush any transport-owned checkpoint before the app is suspended.
    func persist() async
}

extension GameTransport {
    var probeCreatesTurn: Bool { true }

    func persist() async {}
}
