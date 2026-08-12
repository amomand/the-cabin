import XCTest
@testable import TheCabin

/// Health and fear arrive only as a formatted line inside the prose, so the
/// parse has to be exact enough to trust and forgiving enough to fail safely.
final class StatusTests: XCTestCase {
    func testParsesTheStatusLine() {
        let status = Status(statusLine: "Health: 100    Fear: 0")

        XCTAssertEqual(status, Status(statusLine: "Health: 100    Fear: 0"))
        XCTAssertEqual(status?.health, 100)
        XCTAssertEqual(status?.fear, 0)
    }

    func testParsesAnyRunOfWhitespace() {
        XCTAssertEqual(Status(statusLine: "Health: 42 Fear: 7")?.health, 42)
        XCTAssertEqual(Status(statusLine: "Health:\t42\tFear:\t7")?.fear, 7)
    }

    func testRejectsProseThatMerelyMentionsThem() {
        // Anything that fails to parse stays in the transcript, so a false
        // positive would silently eat a line of the story.
        XCTAssertNil(Status(statusLine: "Health: what is left of it"))
        XCTAssertNil(Status(statusLine: "Your health is failing. Fear: 20"))
        XCTAssertNil(Status(statusLine: "Health: 100"))
        XCTAssertNil(Status(statusLine: ""))
        XCTAssertNil(Status(statusLine: "The cold settles into your hands."))
    }
}
