import XCTest
@testable import TheCabin

/// This is intentionally an integration test, not a mock: the iOS simulator
/// loads the bundled Python.framework, imports the packaged game, and advances
/// the real WebGameSession through the Objective-C bridge.
@MainActor
final class EmbeddedPythonIntegrationTests: XCTestCase {
    func testBundledPythonProducesCanonicalFrames() async throws {
        let transport = LocalEngineTransport()

        let intro = try await transport.open()
        XCTAssertEqual(
            intro.lines.joined(separator: " "),
            "You shouldn't have come back. It's awake. It always has been."
        )
        XCTAssertTrue(intro.clear)
        XCTAssertTrue(intro.waitForKey)

        let room = try await transport.send(.keypress)
        XCTAssertEqual(room.prompt, "> ")
        XCTAssertTrue(room.lines.contains("Health: 100    Fear: 0"))

        let ruleTurn = try await transport.send(.input("look"))
        XCTAssertEqual(ruleTurn.prompt, "> ")
        XCTAssertTrue(ruleTurn.lines.contains("Health: 100    Fear: 0"))
    }
}
