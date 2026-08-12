import Foundation

/// The only player-facing lines this client authors.
///
/// Everything else on screen came from the turn core, including its refusals,
/// which arrive already narrated. These three cover the failures the server
/// never gets to speak for: a request that never arrived, an answer that came
/// back unreadable, and a run this client knows it has already lost.
enum Narration {
    static let unreachable = "Nothing answers. The thread will not reach."
    static let unreadable = "The room answers in a shape you cannot read."
    static let threadGoneCold = "That thread has gone cold."
}

extension TransportFailure {
    /// The line to show the player for this failure.
    var narration: String {
        switch self {
        case .narrated(let message), .lost(let message), .busy(let message):
            return message
        case .unreachable:
            return Narration.unreachable
        case .malformed:
            return Narration.unreadable
        }
    }
}
