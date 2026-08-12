import Foundation

/// One frame of output from the turn core, whatever surface produced it.
///
/// The server omits every false flag rather than sending it, so each flag
/// decodes as absent-means-false. `lines` is always present but may be empty.
struct RenderFrame: Codable, Equatable {
    var lines: [String]
    var clear: Bool
    var prompt: String?
    var waitForKey: Bool
    var gameOver: Bool

    enum CodingKeys: String, CodingKey {
        case lines
        case clear
        case prompt
        case waitForKey = "wait_for_key"
        case gameOver = "game_over"
    }

    init(
        lines: [String] = [],
        clear: Bool = false,
        prompt: String? = nil,
        waitForKey: Bool = false,
        gameOver: Bool = false
    ) {
        self.lines = lines
        self.clear = clear
        self.prompt = prompt
        self.waitForKey = waitForKey
        self.gameOver = gameOver
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        // `lines` is the one key the server always writes, so a frame without
        // it is not a frame. Failing here narrates the break; defaulting to
        // empty would show the player a turn where nothing happened.
        lines = try container.decode([String].self, forKey: .lines)
        clear = try container.decodeIfPresent(Bool.self, forKey: .clear) ?? false
        prompt = try container.decodeIfPresent(String.self, forKey: .prompt)
        waitForKey = try container.decodeIfPresent(Bool.self, forKey: .waitForKey) ?? false
        gameOver = try container.decodeIfPresent(Bool.self, forKey: .gameOver) ?? false
    }
}

extension RenderFrame {
    /// What the frame asks of the player.
    enum Mode: String, Codable {
        /// The run is over; nothing more is sent.
        case ended
        /// Any tap acknowledges and moves on.
        case keypress
        /// A command is expected.
        case input
    }

    /// Precedence matches the browser client: over means over, then a
    /// keypress, then anything else takes a command.
    var mode: Mode {
        if gameOver { return .ended }
        if waitForKey { return .keypress }
        return .input
    }
}

/// The body of `POST /session`, which nests the first frame beside the token.
struct SessionCreation: Decodable {
    let token: String
    let frame: RenderFrame
}

/// Every non-200 carries a narrated line rather than framework text.
struct NarratedFailure: Decodable {
    let message: String
}
