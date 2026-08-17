import XCTest
@testable import TheCabin

final class PlaytestNoteTests: XCTestCase {
    func testStorySnapshotKeepsOnlySmallLegibleStoryFields() throws {
        let clientID = String(repeating: "a", count: 43)
        let snapshot = PlaytestStorySnapshot(
            act: "api_key=sk-this-must-not-leave",
            location: clientID,
            worldLayer: "wrong",
            markers: ["door_open", "resume_handle=secret", "Bearer hidden"]
        )

        XCTAssertNil(snapshot.act)
        XCTAssertNil(snapshot.location)
        XCTAssertEqual(snapshot.worldLayer, "wrong")
        XCTAssertEqual(snapshot.markers, ["door_open"])

        let encoded = String(decoding: try JSONEncoder().encode(snapshot), as: UTF8.self)
        XCTAssertFalse(encoded.contains("sk-this-must-not-leave"))
        XCTAssertFalse(encoded.contains(clientID))
        XCTAssertFalse(encoded.contains("secret"))
    }

    func testDecodedStorySnapshotIsSanitizedAgain() throws {
        let unsafe = Data(
            #"{"act":"Act III","location":"client_id=hidden","worldLayer":"wrong","markers":["safe","sk-hidden-secret-key"]}"#.utf8
        )

        let snapshot = try JSONDecoder().decode(PlaytestStorySnapshot.self, from: unsafe)

        XCTAssertEqual(snapshot.act, "Act III")
        XCTAssertNil(snapshot.location)
        XCTAssertEqual(snapshot.worldLayer, "wrong")
        XCTAssertEqual(snapshot.markers, ["safe"])
    }
}
