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

    func testCredentialNamesCannotBypassSanitizingWithPunctuation() throws {
        let unsafe = Data(
            #"{"act":"API key: hidden","location":"client-id: confidential","worldLayer":"resume handle: short-token","markers":["Bearer-token", "access-token: short-token", "session token: short-token", "door_open"]}"#.utf8
        )

        let snapshot = try JSONDecoder().decode(PlaytestStorySnapshot.self, from: unsafe)

        XCTAssertNil(snapshot.act)
        XCTAssertNil(snapshot.location)
        XCTAssertNil(snapshot.worldLayer)
        XCTAssertEqual(snapshot.markers, ["door_open"])
    }

    func testCredentialFilterDoesNotRejectAnOrdinaryBearerWord() {
        let snapshot = PlaytestStorySnapshot(
            location: "Bearerfish cove",
            markers: ["door_open", "secret_room"]
        )

        XCTAssertEqual(snapshot.location, "Bearerfish cove")
        XCTAssertEqual(snapshot.markers, ["door_open", "secret_room"])
    }
}
