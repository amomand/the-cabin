import XCTest
@testable import TheCabin

final class PlaytestNoteStoreTests: XCTestCase {
    private var directory: URL!
    private var store: PlaytestNoteStore!

    override func setUpWithError() throws {
        directory = URL(fileURLWithPath: NSTemporaryDirectory())
            .appendingPathComponent(UUID().uuidString)
        store = PlaytestNoteStore(directory: directory)
    }

    override func tearDownWithError() throws {
        try? FileManager.default.removeItem(at: directory)
    }

    func testAppendIsStructuredAndSurvivesRelaunch() throws {
        let first = note(1)
        let second = note(2)

        XCTAssertTrue(store.append(first))
        XCTAssertTrue(store.append(second))

        let relaunched = PlaytestNoteStore(directory: directory)
        XCTAssertEqual(relaunched.load(), [first, second])

        let archive = try JSONSerialization.jsonObject(
            with: Data(contentsOf: archiveURL)
        ) as? [String: Any]
        XCTAssertEqual(archive?["schemaVersion"] as? Int, 1)
        XCTAssertEqual((archive?["notes"] as? [Any])?.count, 2)
    }

    func testMalformedArchiveIsNotOverwrittenByAnAppend() throws {
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        let damaged = Data("{ not json".utf8)
        try damaged.write(to: archiveURL)

        XCTAssertTrue(store.load().isEmpty)
        XCTAssertFalse(store.append(note(1)))
        XCTAssertEqual(try Data(contentsOf: archiveURL), damaged)
    }

    func testTruncatedArchiveIsNotOverwrittenByAnAppend() throws {
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        let truncated = Data(#"{"schemaVersion":1,"notes":[{"id":"#.utf8)
        try truncated.write(to: archiveURL)

        XCTAssertTrue(store.load().isEmpty)
        XCTAssertFalse(store.append(note(1)))
        XCTAssertEqual(try Data(contentsOf: archiveURL), truncated)
    }

    func testRapidAppendsLoseNoPages() {
        let expected = Set((0..<60).map { "Note \($0)" })

        DispatchQueue.concurrentPerform(iterations: expected.count) { index in
            _ = store.append(note(index))
        }

        let loaded = store.load()
        XCTAssertEqual(loaded.count, expected.count)
        XCTAssertEqual(Set(loaded.map(\.body)), expected)
    }

    func testRapidAppendsAcrossStoreInstancesLoseNoPages() {
        let expected = Set((0..<60).map { "Note \($0)" })

        DispatchQueue.concurrentPerform(iterations: expected.count) { index in
            _ = PlaytestNoteStore(directory: directory).append(note(index))
        }

        let loaded = store.load()
        XCTAssertEqual(loaded.count, expected.count)
        XCTAssertEqual(Set(loaded.map(\.body)), expected)
    }

    func testMarkdownExportIsDeterministic() throws {
        let snapshot = PlaytestStorySnapshot(
            act: "Act II",
            location: "Cabin kitchen",
            worldLayer: "wrong",
            markers: ["fire_lit", "door_open"]
        )
        let note = PlaytestNote(
            id: UUID(uuidString: "D4186180-5E8D-45D2-A139-5B8C4D9439EF")!,
            context: PlaytestNoteContext(
                capturedAt: Date(timeIntervalSince1970: 0),
                successfulTurnIndex: 7,
                recentTranscript: [
                    PlaytestTranscriptLine(kind: .echo, text: "> listen"),
                    PlaytestTranscriptLine(kind: .narration, text: "Nothing.\nThen the wall."),
                ],
                status: Status(statusLine: "Health: 90    Fear: 12"),
                story: snapshot
            ),
            body: "The second line arrives late."
        )
        XCTAssertTrue(store.append(note))

        let first = try XCTUnwrap(store.prepareMarkdownExport())
        let firstBytes = try Data(contentsOf: first)
        let second = try XCTUnwrap(store.prepareMarkdownExport())
        let secondBytes = try Data(contentsOf: second)

        XCTAssertEqual(first.lastPathComponent, PlaytestNoteStore.exportFilename)
        XCTAssertEqual(firstBytes, secondBytes)
        XCTAssertEqual(
            String(decoding: firstBytes, as: UTF8.self),
            """
            # The Cabin playtest notes

            ## Note 1

            - Captured: `1970-01-01T00:00:00.000Z`
            - Successful turn: 7
            - Health: 90
            - Fear: 12
            - Act: Act II
            - Location: Cabin kitchen
            - World layer: wrong
            - Story markers: door_open, fire_lit

            ### Recent transcript

            - `echo`: > listen
            - `narration`: Nothing. ↵ Then the wall.

            ### Observation

            The second line arrives late.


            """
        )
    }

    private var archiveURL: URL {
        directory.appendingPathComponent(PlaytestNoteStore.archiveFilename)
    }

    private func note(_ index: Int) -> PlaytestNote {
        PlaytestNote(
            id: UUID(),
            context: PlaytestNoteContext(
                capturedAt: Date(timeIntervalSince1970: TimeInterval(index)),
                successfulTurnIndex: index,
                recentTranscript: [],
                status: nil,
                story: nil
            ),
            body: "Note \(index)"
        )
    }
}
