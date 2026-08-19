import UIKit
import XCTest
@testable import TheCabin

/// The turn core writes a few lines the way a terminal would. The layout has
/// to recognise exactly those shapes, and leave everything else as prose.
final class TranscriptLayoutTests: XCTestCase {
    private func narration(_ lines: [String]) -> [TranscriptBlock] {
        lines.map { TranscriptBlock(kind: .narration, text: $0) }
    }

    func testRoomNameBeforeDashesIsATitleAndTheDashesARule() {
        let roles = TranscriptRole.roles(for: narration(["Wilderness", "----------", "The gravel drive."]))
        XCTAssertEqual(roles, [.title, .rule, .body])
    }

    func testALongBoxRuleIsARuleWithoutATitle() {
        let roles = TranscriptRole.roles(for: narration(["Prose.", String(repeating: "\u{2500}", count: 79)]))
        XCTAssertEqual(roles, [.body, .rule])
        XCTAssertEqual(TranscriptRole.roles(for: narration(["--"])), [.body])
    }

    func testAsteriskWrappedLineIsAnAsideWithMarkersDropped() {
        XCTAssertEqual(
            TranscriptRole.roles(for: narration(["*Pull yourself back.*"])),
            [.aside("Pull yourself back.")]
        )
        XCTAssertEqual(TranscriptRole.roles(for: narration(["*"])), [.body])
        XCTAssertEqual(TranscriptRole.roles(for: narration(["*a sentence with a *star* inside"])), [.body])
    }

    func testEmptyLineIsAGap() {
        XCTAssertEqual(TranscriptRole.roles(for: narration(["", "  "])), [.gap, .gap])
    }

    func testOnlyTheRoomsOwnLinesTakeRoles() {
        let blocks = [
            TranscriptBlock(kind: .echo, text: "> ----"),
            TranscriptBlock(kind: .refusal, text: ""),
            TranscriptBlock(kind: .echo, text: "look"),
            TranscriptBlock(kind: .narration, text: "----"),
        ]
        // The dashes after a player's echo do not make the echo a title.
        XCTAssertEqual(TranscriptRole.roles(for: blocks), [.body, .body, .body, .rule])
    }

    func testTheItalicAndBoldBookFacesExistOnIOS() {
        XCTAssertNotNil(UIFont(name: Theme.bookItalicFontName, size: 17))
        XCTAssertNotNil(UIFont(name: Theme.bookBoldFontName, size: 19))
    }
}
