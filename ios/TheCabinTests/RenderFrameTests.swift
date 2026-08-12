import XCTest
@testable import TheCabin

/// The server omits every false flag rather than sending it, so the decoder has
/// to treat absence as false rather than as a missing key.
final class RenderFrameTests: XCTestCase {
    private func frame(_ json: String) throws -> RenderFrame {
        try JSONDecoder().decode(RenderFrame.self, from: Data(json.utf8))
    }

    func testDecodesTheIntroFrame() throws {
        let decoded = try frame("""
        {"type":"render","lines":["You shouldn't have come back.","It's awake.",\
        "It always has been."],"clear":true,"wait_for_key":true}
        """)

        XCTAssertEqual(decoded.lines.count, 3)
        XCTAssertTrue(decoded.clear)
        XCTAssertTrue(decoded.waitForKey)
        XCTAssertFalse(decoded.gameOver)
        XCTAssertNil(decoded.prompt)
        XCTAssertEqual(decoded.mode, .keypress)
    }

    func testOmittedFlagsDecodeAsFalse() throws {
        let decoded = try frame(#"{"type":"render","lines":[],"prompt":"> "}"#)

        XCTAssertFalse(decoded.clear)
        XCTAssertFalse(decoded.waitForKey)
        XCTAssertFalse(decoded.gameOver)
        XCTAssertEqual(decoded.prompt, "> ")
        XCTAssertEqual(decoded.lines, [])
    }

    func testAFrameWithNoFlagsAtAllStillTakesInput() throws {
        // The browser client's fallback: no game_over, no wait_for_key and no
        // prompt still means a command is expected.
        let decoded = try frame(#"{"type":"render","lines":["The cold settles."]}"#)

        XCTAssertEqual(decoded.mode, .input)
    }

    func testGameOverOutranksWaitForKey() throws {
        let decoded = try frame(#"{"type":"render","lines":[],"wait_for_key":true,"game_over":true}"#)

        XCTAssertEqual(decoded.mode, .ended)
    }

    func testWaitForKeyOutranksPrompt() throws {
        let decoded = try frame(#"{"type":"render","lines":[],"prompt":"> ","wait_for_key":true}"#)

        XCTAssertEqual(decoded.mode, .keypress)
    }

    func testAFrameWithoutLinesIsNotAFrame() {
        // The server always writes `lines`. Defaulting a missing one to empty
        // would render a turn in which nothing happened; failing to decode
        // narrates the break instead.
        XCTAssertThrowsError(try frame(#"{"type":"render","prompt":"> "}"#))
    }

    func testSessionCreationNestsItsFrame() throws {
        let json = #"{"token":"abc123","frame":{"type":"render","lines":["It's awake."],"clear":true,"wait_for_key":true}}"#

        let created = try JSONDecoder().decode(SessionCreation.self, from: Data(json.utf8))

        XCTAssertEqual(created.token, "abc123")
        XCTAssertEqual(created.frame.lines, ["It's awake."])
        XCTAssertEqual(created.frame.mode, .keypress)
    }

    func testNarratedFailureDecodes() throws {
        let json = #"{"type":"error","message":"That thread has gone cold. The room remembers nothing of it."}"#

        let failure = try JSONDecoder().decode(NarratedFailure.self, from: Data(json.utf8))

        XCTAssertEqual(failure.message, "That thread has gone cold. The room remembers nothing of it.")
    }
}
