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
