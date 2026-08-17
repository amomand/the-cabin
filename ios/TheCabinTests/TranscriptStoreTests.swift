import XCTest
@testable import TheCabin

final class TranscriptStoreTests: XCTestCase {
    private var directory: URL!

    override func setUpWithError() throws {
        directory = URL(fileURLWithPath: NSTemporaryDirectory())
            .appendingPathComponent(UUID().uuidString)
    }

    override func tearDownWithError() throws {
        try? FileManager.default.removeItem(at: directory)
    }

    func testRoundTripsARun() {
        let store = TranscriptStore(directory: directory)
        let run = PersistedRun(
            resumeHandle: "token",
            blocks: [
                TranscriptBlock(kind: .narration, text: "It's awake."),
                TranscriptBlock(kind: .echo, text: "> look"),
            ],
            status: Status(statusLine: "Health: 90    Fear: 12"),
            mode: .keypress,
            prompt: nil,
            pendingTurn: .input("look")
        )

        store.save(run)

        XCTAssertEqual(store.load(), run)
    }

    func testLoadsARunWrittenBeforeOpenerMetadataExisted() throws {
        struct LegacyRun: Encodable {
            let resumeHandle: String?
            let blocks: [TranscriptBlock]
            let status: Status?
            let mode: RenderFrame.Mode
            let prompt: String?
            let pendingTurn: PlayerTurn?
        }
        let legacy = LegacyRun(
            resumeHandle: "token",
            blocks: [TranscriptBlock(kind: .narration, text: "The door hangs open.")],
            status: Status(statusLine: "Health: 90    Fear: 12"),
            mode: .input,
            prompt: "> ",
            pendingTurn: nil
        )
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        try JSONEncoder().encode(legacy).write(
            to: directory.appendingPathComponent("run.json"),
            options: .atomic
        )

        let run = TranscriptStore(directory: directory).load()

        XCTAssertEqual(run?.resumeHandle, "token")
        XCTAssertEqual(run?.blocks.map(\.text), ["The door hangs open."])
        XCTAssertNil(run?.openerLines)
        XCTAssertNil(run?.isAtRunOpener)
        XCTAssertNil(run?.successfulTurnIndex)
    }

    func testLoadsNothingBeforeAnythingIsSaved() {
        XCTAssertNil(TranscriptStore(directory: directory).load())
    }

    func testAHalfWrittenFileIsNotFatal() throws {
        let store = TranscriptStore(directory: directory)
        store.save(.empty)
        try Data("{ not json".utf8).write(to: directory.appendingPathComponent("run.json"))

        // A relaunch on a corrupt file starts a fresh run rather than crashing.
        XCTAssertNil(store.load())
    }

    func testClearRemovesTheRun() {
        let store = TranscriptStore(directory: directory)
        store.save(.empty)

        store.clear()

        XCTAssertNil(store.load())
    }
}
