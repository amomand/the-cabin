import XCTest
@testable import TheCabin

/// A clock the tests move by hand, so the grace period on liveness checks can
/// be tested without waiting it out.
private final class TestClock {
    var now = Date(timeIntervalSince1970: 1_000_000)
}

@MainActor
final class GameSessionTests: XCTestCase {
    private var directory: URL!
    private var store: TranscriptStore!
    private var noteStore: PlaytestNoteStore!
    private var transport: StubTransport!
    private var clock: TestClock!
    private var session: GameSession!

    override func setUpWithError() throws {
        directory = URL(fileURLWithPath: NSTemporaryDirectory())
            .appendingPathComponent(UUID().uuidString)
        store = TranscriptStore(directory: directory)
        noteStore = PlaytestNoteStore(directory: directory)
        transport = StubTransport()
        let clock = TestClock()
        self.clock = clock
        session = GameSession(
            transport: transport,
            store: store,
            playtestNoteStore: noteStore,
            now: { clock.now }
        )
    }

    override func tearDownWithError() throws {
        try? FileManager.default.removeItem(at: directory)
    }

    private static let intro = RenderFrame(
        lines: ["You shouldn't have come back.", "It's awake."],
        clear: true,
        waitForKey: true
    )

    private static let room = RenderFrame(
        lines: ["The door hangs open.", "Health: 100    Fear: 0"],
        prompt: "> "
    )

    func testStartOpensARunAndRendersIt() async {
        transport.openResults = [.success(Self.intro)]

        await session.start()

        XCTAssertEqual(transport.opens, 1)
        XCTAssertEqual(session.blocks.map(\.text), ["You shouldn't have come back.", "It's awake."])
        XCTAssertEqual(session.mode, .keypress)
        XCTAssertNil(session.launchOpenerLines, "A new run renders its real opening frame")
    }

    func testAFirstLaunchFailureCanBeRetriedOnTheNextTap() async {
        transport.openResults = [.failure(.unreachable), .success(Self.intro)]

        await session.start()

        XCTAssertEqual(session.mode, .ended)
        XCTAssertEqual(session.blocks.map(\.text), [Narration.unreachable])

        await session.acknowledge()

        XCTAssertEqual(transport.opens, 2)
        XCTAssertTrue(transport.sent.isEmpty, "There is no run to advance before the retry")
        XCTAssertEqual(session.mode, .keypress)
        XCTAssertEqual(
            session.blocks.map(\.text),
            ["You shouldn't have come back.", "It's awake."],
            "The successful retry begins on the authored intro"
        )
    }

    func testTheStatusLineLeavesTheTranscript() async {
        transport.openResults = [.success(Self.room)]

        await session.start()

        XCTAssertEqual(session.blocks.map(\.text), ["The door hangs open."])
        XCTAssertEqual(session.status?.health, 100)
        XCTAssertEqual(session.status?.fear, 0)
        XCTAssertEqual(session.mode, .input)
    }

    func testClearStartsAFreshScreen() async {
        transport.openResults = [.success(Self.room)]
        transport.sendResults = [.success(RenderFrame(lines: ["Somewhere else."], clear: true, prompt: "> "))]
        await session.start()

        await session.submit("north")

        XCTAssertEqual(session.blocks.map(\.text), ["Somewhere else."])
    }

    func testSubmitEchoesUnderThePromptTheServerSent() async {
        transport.openResults = [.success(Self.room)]
        transport.sendResults = [.success(RenderFrame(lines: ["Nothing there."], prompt: "> "))]
        await session.start()

        await session.submit("  look  ")

        XCTAssertEqual(transport.sent, [.input("look")])
        XCTAssertEqual(session.blocks.map(\.text), ["The door hangs open.", "> look", "Nothing there."])
    }

    func testABlankCommandIsNotSent() async {
        transport.openResults = [.success(Self.room)]
        await session.start()

        await session.submit("   ")

        XCTAssertTrue(transport.sent.isEmpty)
    }

    func testAcknowledgeSendsAKeypressOnlyWhileOneIsWanted() async {
        transport.openResults = [.success(Self.intro)]
        transport.sendResults = [.success(Self.room)]
        await session.start()

        await session.acknowledge()
        XCTAssertEqual(transport.sent, [.keypress])

        // Now the run wants a command, so a tap must not send anything.
        await session.acknowledge()
        XCTAssertEqual(transport.sent, [.keypress])
    }

    func testABusyTurnWaitsBehindATapThenRetriesUnchanged() async {
        transport.openResults = [.success(Self.room)]
        transport.sendResults = [
            .failure(.busy("The room needs a moment to settle.")),
            .success(RenderFrame(lines: ["The door gives."], prompt: "> ")),
        ]
        await session.start()

        await session.submit("look")

        XCTAssertEqual(session.blocks.last?.text, "The room needs a moment to settle.")
        XCTAssertEqual(session.blocks.last?.kind, .refusal)
        XCTAssertEqual(session.mode, .keypress)

        await session.acknowledge()

        XCTAssertEqual(transport.sent, [.input("look"), .input("look")])
        XCTAssertEqual(session.blocks.last?.text, "The door gives.")
        XCTAssertEqual(session.mode, .input)
        XCTAssertEqual(transport.opens, 1, "Nothing was lost, so nothing should be reopened")
    }

    func testAnUnreachableTurnIsNarratedAndRetriedWithoutRetyping() async {
        transport.openResults = [.success(Self.room)]
        transport.sendResults = [
            .failure(.unreachable),
            .success(RenderFrame(lines: ["The room answers."], prompt: "> ")),
        ]
        await session.start()

        await session.submit("look")

        XCTAssertEqual(session.blocks.last?.text, Narration.unreachable)
        XCTAssertEqual(session.mode, .keypress)

        await session.acknowledge()

        XCTAssertEqual(transport.sent, [.input("look"), .input("look")])
        XCTAssertEqual(session.blocks.last?.text, "The room answers.")
        XCTAssertEqual(session.mode, .input)
    }

    func testALostRunHoldsOnItsNarrationRatherThanRestartingUnderThePlayer() async {
        transport.openResults = [.success(Self.room), .success(Self.intro)]
        transport.sendResults = [.failure(.lost("That thread has gone cold."))]
        await session.start()

        await session.submit("look")

        // Opening a new run here would clear the screen, and the line the
        // player is still reading with it.
        XCTAssertEqual(transport.opens, 1)
        XCTAssertEqual(session.mode, .ended)
        XCTAssertEqual(session.blocks.last?.text, "That thread has gone cold.")
        XCTAssertNil(session.status, "The old run's readings do not belong to whatever comes next")
    }

    func testATapAfterALostRunBeginsAgainOnTheAuthoredIntro() async {
        transport.openResults = [.success(Self.room), .success(Self.intro)]
        transport.sendResults = [.failure(.lost("That thread has gone cold."))]
        await session.start()
        await session.submit("look")

        await session.acknowledge()

        XCTAssertEqual(transport.opens, 2)
        XCTAssertEqual(session.mode, .keypress)
        XCTAssertEqual(
            session.blocks.map(\.text),
            ["You shouldn't have come back.", "It's awake."],
            "The intro is authored prose, so it reads as the restart without the client writing one"
        )
    }

    func testRelaunchHoldsALostRunUntilThePlayerTaps() async {
        transport.openResults = [.success(Self.room)]
        transport.sendResults = [.failure(.lost("That thread has gone cold."))]
        await session.start()
        await session.submit("look")

        let relaunchedTransport = StubTransport()
        relaunchedTransport.openResults = [.success(Self.intro)]
        let relaunched = GameSession(transport: relaunchedTransport, store: store)
        relaunched.restore()

        await relaunched.start()

        XCTAssertEqual(relaunchedTransport.opens, 0, "Relaunch must not clear the ending before a tap")
        XCTAssertEqual(relaunched.mode, .ended)
        XCTAssertEqual(relaunched.blocks.last?.text, "That thread has gone cold.")
        XCTAssertEqual(relaunched.launchOpenerLines, LaunchOpener.legacyFallbackLines)

        await relaunched.acknowledge()
        XCTAssertEqual(relaunchedTransport.opens, 0, "The cover prevents input reaching the ended run")

        relaunched.dismissLaunchOpener()
        XCTAssertEqual(relaunchedTransport.opens, 0, "Removing the cover does not begin another run")

        await relaunched.acknowledge()

        XCTAssertEqual(relaunchedTransport.opens, 1)
        XCTAssertEqual(relaunched.mode, .keypress)
        XCTAssertEqual(relaunched.blocks.map(\.text), ["You shouldn't have come back.", "It's awake."])
    }

    func testAFailedRestartStaysWhereItIsAndCanBeTappedAgain() async {
        transport.openResults = [.success(Self.room), .failure(.unreachable), .success(Self.intro)]
        transport.sendResults = [.failure(.lost("That thread has gone cold."))]
        await session.start()
        await session.submit("look")

        await session.acknowledge()
        XCTAssertEqual(session.mode, .ended, "Still ended, so the next tap can try again")
        XCTAssertEqual(session.blocks.last?.text, Narration.unreachable)

        await session.acknowledge()
        XCTAssertEqual(transport.opens, 3)
        XCTAssertEqual(session.mode, .keypress)
    }

    func testGameOverEndsTheRunAndATapBeginsAnother() async {
        transport.openResults = [.success(Self.room), .success(Self.intro)]
        transport.sendResults = [.success(RenderFrame(lines: ["The cold has had its turn."], gameOver: true))]
        await session.start()
        await session.submit("wait")
        XCTAssertEqual(session.mode, .ended)

        await session.acknowledge()

        XCTAssertEqual(transport.opens, 2)
        XCTAssertEqual(session.mode, .keypress)
    }

    func testAnAbandonedWaitSaysNothing() async {
        transport.openResults = [.success(Self.room)]
        transport.sendResults = [
            .success(RenderFrame(lines: ["The room answers."], prompt: "> "))
        ]
        await session.start()
        transport.cancelNextSend = true

        await session.submit("look")

        // The echo is the player's own, but the room must not be made to
        // answer a question that was never finished being asked.
        XCTAssertEqual(session.blocks.map(\.text), ["The door hangs open.", "> look"])
        XCTAssertEqual(session.mode, .keypress)

        await session.acknowledge()

        XCTAssertEqual(transport.sent, [.input("look"), .input("look")])
        XCTAssertEqual(session.blocks.last?.text, "The room answers.")
    }

    func testAnUnansweredTurnSurvivesRelaunchAndRetriesOnATap() async {
        transport.openResults = [.success(Self.room)]
        transport.sendResults = [.failure(.unreachable)]
        await session.start()
        await session.submit("look")

        let resumed = StubTransport()
        resumed.sendResults = [
            .success(RenderFrame(lines: ["The room answers."], prompt: "> "))
        ]
        let relaunched = GameSession(transport: resumed, store: store)
        relaunched.restore()

        await relaunched.start()
        XCTAssertEqual(resumed.probes, 0, "A pending turn must be replayed, not probed past")
        XCTAssertEqual(relaunched.mode, .keypress)

        await relaunched.acknowledge()
        XCTAssertTrue(resumed.sent.isEmpty, "The cold-launch cover cannot retry the pending turn")

        relaunched.dismissLaunchOpener()

        await relaunched.acknowledge()

        XCTAssertEqual(resumed.sent, [.input("look")])
        XCTAssertEqual(relaunched.blocks.last?.text, "The room answers.")
        XCTAssertEqual(relaunched.mode, .input)
    }

    func testANewRunDoesNotInheritTheLastOnesReadings() async {
        transport.openResults = [.success(Self.room), .success(Self.intro)]
        transport.sendResults = [.success(RenderFrame(lines: ["The cold has had its turn."], gameOver: true))]
        await session.start()
        await session.submit("wait")
        XCTAssertEqual(session.status?.health, 100, "Still the old run's, which is right until it ends")

        await session.acknowledge()

        // The intro has no status line of its own, so a stale one would sit
        // above a run that has not started.
        XCTAssertNil(session.status)
    }

    // MARK: - Restoring

    func testNotebookFreezesRecentContextWhenItOpens() async {
        var story = PlaytestStorySnapshot(
            act: "Act I",
            location: "Cabin porch",
            markers: ["arrived"]
        )
        let contextual = GameSession(
            transport: transport,
            store: store,
            playtestNoteStore: noteStore,
            storySnapshot: { story },
            now: { self.clock.now }
        )
        let contextFrame = RenderFrame(
            lines: (0..<10).map { "Line \($0)." } + ["Health: 100    Fear: 0"],
            prompt: "> "
        )
        transport.openResults = [.success(contextFrame)]
        transport.sendResults = [
            .success(RenderFrame(lines: ["The latch lifts."], prompt: "> "))
        ]
        await contextual.start()

        contextual.beginPlaytestNote()
        let frozen = contextual.playtestNoteDraft?.context

        clock.now += 10
        story = PlaytestStorySnapshot(act: "Act II", location: "Kitchen")
        await contextual.submit("open door")

        XCTAssertEqual(frozen?.capturedAt, Date(timeIntervalSince1970: 1_000_000))
        XCTAssertEqual(frozen?.successfulTurnIndex, 0)
        XCTAssertEqual(
            frozen?.recentTranscript.map(\.text),
            (2..<10).map { "Line \($0)." }
        )
        XCTAssertEqual(frozen?.status, Status(statusLine: "Health: 100    Fear: 0"))
        XCTAssertEqual(frozen?.story?.act, "Act I")
        XCTAssertEqual(contextual.playtestNoteDraft?.context, frozen)
        XCTAssertEqual(contextual.successfulTurnIndex, 1)
    }

    func testEmptyAndCancelledPagesAppendNothing() {
        session.beginPlaytestNote()
        XCTAssertFalse(session.savePlaytestNote())
        session.updatePlaytestNote("   \n")
        XCTAssertFalse(session.savePlaytestNote())

        session.cancelPlaytestNote()

        XCTAssertNil(session.playtestNoteDraft)
        XCTAssertTrue(noteStore.load().isEmpty)
    }

    func testSavedPageSurvivesRelaunch() async {
        transport.openResults = [.success(Self.room)]
        await session.start()
        session.beginPlaytestNote()
        session.updatePlaytestNote("  The status line lags.  ")

        XCTAssertTrue(session.savePlaytestNote())

        XCTAssertNil(session.playtestNoteDraft)
        XCTAssertNotNil(session.playtestNotesExportURL)
        let relaunched = PlaytestNoteStore(directory: directory)
        XCTAssertEqual(relaunched.load().map(\.body), ["The status line lags."])
    }

    func testPendingRetryIncrementsExactlyOnceAcrossRelaunch() async {
        transport.openResults = [.success(Self.room)]
        transport.sendResults = [.failure(.unreachable)]
        await session.start()

        await session.submit("look")
        XCTAssertEqual(session.successfulTurnIndex, 0)

        let resumed = StubTransport()
        resumed.sendResults = [
            .success(RenderFrame(lines: ["The room answers."], prompt: "> "))
        ]
        let relaunched = GameSession(
            transport: resumed,
            store: store,
            playtestNoteStore: noteStore
        )
        relaunched.restore()
        await relaunched.start()
        XCTAssertEqual(relaunched.successfulTurnIndex, 0)
        relaunched.dismissLaunchOpener()

        await relaunched.acknowledge()

        XCTAssertEqual(resumed.sent, [.input("look")])
        XCTAssertEqual(relaunched.successfulTurnIndex, 1)
        XCTAssertEqual(store.load()?.successfulTurnIndex, 1)
    }

    func testCancelledLivenessRetryDoesNotBecomeASuccessfulPlayerTurn() async {
        transport.openResults = [.success(Self.room)]
        transport.sendResults = [
            .success(RenderFrame(lines: ["The room answers."], prompt: "> "))
        ]
        await session.start()
        await session.submit("look")
        XCTAssertEqual(session.successfulTurnIndex, 1)

        let resumed = StubTransport()
        resumed.cancelNextProbe = true
        resumed.sendResults = [
            .success(RenderFrame(lines: [], prompt: "> "))
        ]
        let relaunched = GameSession(
            transport: resumed,
            store: store,
            playtestNoteStore: noteStore
        )
        relaunched.restore()
        relaunched.dismissLaunchOpener()

        await relaunched.start()
        await relaunched.acknowledge()

        XCTAssertEqual(resumed.sent, [.input("")])
        XCTAssertEqual(relaunched.successfulTurnIndex, 1)
        XCTAssertEqual(store.load()?.successfulTurnIndex, 1)
    }

    func testLegacyRunWithoutTurnIndexRestoresAtZero() {
        store.save(
            PersistedRun(
                resumeHandle: "legacy-token",
                blocks: [TranscriptBlock(kind: .narration, text: "The door hangs open.")],
                status: nil,
                mode: .input,
                prompt: "> ",
                successfulTurnIndex: nil
            )
        )
        let relaunched = GameSession(
            transport: StubTransport(),
            store: store,
            playtestNoteStore: noteStore
        )

        relaunched.restore()

        XCTAssertEqual(relaunched.successfulTurnIndex, 0)
    }

    func testOpaqueRuntimeStateNeverEntersNotebookOrExport() throws {
        let resumeSecret = "resume-handle-secret"
        let clientSecret = "client-id-secret"
        let apiSecret = "sk-api-key-secret"
        transport.adopt(
            resumeHandle: [resumeSecret, clientSecret, apiSecret].joined(separator: ".")
        )
        session.beginPlaytestNote()
        session.updatePlaytestNote("The cursor sticks after the line.")

        XCTAssertTrue(session.savePlaytestNote())

        let archive = String(
            decoding: try Data(
                contentsOf: directory.appendingPathComponent(PlaytestNoteStore.archiveFilename)
            ),
            as: UTF8.self
        )
        let exportURL = try XCTUnwrap(session.playtestNotesExportURL)
        let markdown = String(decoding: try Data(contentsOf: exportURL), as: UTF8.self)
        for secret in [resumeSecret, clientSecret, apiSecret] {
            XCTAssertFalse(archive.contains(secret))
            XCTAssertFalse(markdown.contains(secret))
        }
    }

    func testColdRelaunchCoversButDoesNotReplaceAnActiveRun() async {
        let authoredOpener = RenderFrame(
            lines: ["You shouldn't have come back.", "It's awake.", "It always has been."],
            clear: true,
            waitForKey: true
        )
        transport.openResults = [.success(authoredOpener)]
        transport.sendResults = [.success(Self.room)]
        await session.start()
        await session.acknowledge()
        let savedBlocks = session.blocks
        let savedStatus = session.status
        let savedMode = session.mode

        let resumed = StubTransport()
        let relaunched = GameSession(transport: resumed, store: store)
        relaunched.restore()

        XCTAssertEqual(relaunched.launchOpenerLines, authoredOpener.lines)
        XCTAssertEqual(relaunched.blocks, savedBlocks)
        XCTAssertEqual(relaunched.status, savedStatus)
        XCTAssertEqual(relaunched.mode, savedMode)

        await relaunched.start()
        XCTAssertEqual(resumed.probes, 0, "The restored run stays untouched behind its cover")

        relaunched.dismissLaunchOpener()

        XCTAssertNil(relaunched.launchOpenerLines)
        XCTAssertEqual(relaunched.blocks, savedBlocks)
        XCTAssertEqual(relaunched.status, savedStatus)
        XCTAssertEqual(relaunched.mode, savedMode)
        XCTAssertEqual(resumed.opens, 0)
        XCTAssertTrue(resumed.sent.isEmpty, "The cover tap sends no turn")
    }

    func testAFailedProbeCannotMutateTheRunBehindTheColdLaunchCover() async {
        transport.openResults = [.success(Self.room)]
        await session.start()
        let savedBlocks = session.blocks
        let savedStatus = session.status
        let savedMode = session.mode
        let savedPrompt = session.prompt

        let resumed = StubTransport()
        resumed.probeResults = [.failure(.unreachable)]
        let relaunched = GameSession(transport: resumed, store: store)
        relaunched.restore()

        await relaunched.start()
        await relaunched.resumeFromBackground()
        relaunched.dismissLaunchOpener()

        XCTAssertEqual(resumed.probes, 0)
        XCTAssertEqual(relaunched.blocks, savedBlocks)
        XCTAssertEqual(relaunched.status, savedStatus)
        XCTAssertEqual(relaunched.mode, savedMode)
        XCTAssertEqual(relaunched.prompt, savedPrompt)
        XCTAssertTrue(resumed.sent.isEmpty)
    }

    func testColdRelaunchWhileTheRealOpenerIsShowingDoesNotDoubleIt() async {
        transport.openResults = [.success(Self.intro)]
        await session.start()

        let resumed = StubTransport()
        resumed.sendResults = [
            .success(
                RenderFrame(
                    lines: ["The door hangs open.", "Health: 100    Fear: 0"],
                    clear: true,
                    prompt: "> "
                )
            )
        ]
        let relaunched = GameSession(transport: resumed, store: store)
        relaunched.restore()

        XCTAssertNil(relaunched.launchOpenerLines, "The persisted screen is already the real opener")
        await relaunched.start()
        XCTAssertEqual(resumed.probes, 0, "A keypress frame must not be probed")

        await relaunched.acknowledge()

        XCTAssertEqual(resumed.sent, [.keypress])
        XCTAssertEqual(relaunched.blocks.map(\.text), ["The door hangs open."])
    }

    func testLegacyRunAtTheRealOpenerDoesNotGainASecondCover() {
        store.save(
            PersistedRun(
                resumeHandle: "legacy-token",
                blocks: LaunchOpener.legacyFallbackLines.map {
                    TranscriptBlock(kind: .narration, text: $0)
                },
                status: nil,
                mode: .keypress,
                prompt: nil,
                pendingTurn: nil
            )
        )
        let relaunched = GameSession(transport: StubTransport(), store: store)

        relaunched.restore()

        XCTAssertNil(relaunched.launchOpenerLines)
    }

    func testForegroundingDoesNotReplayADismissedLaunchCover() async {
        transport.openResults = [.success(Self.room)]
        await session.start()

        let resumed = StubTransport()
        let relaunched = GameSession(transport: resumed, store: store, now: { self.clock.now })
        relaunched.restore()
        XCTAssertNotNil(relaunched.launchOpenerLines)
        relaunched.dismissLaunchOpener()
        await relaunched.start()
        clock.now += 3600

        await relaunched.resumeFromBackground()

        XCTAssertNil(relaunched.launchOpenerLines)
        XCTAssertEqual(resumed.probes, 2)
    }

    func testRestorePutsTheScreenBackWithoutTheNetwork() async {
        transport.openResults = [.success(Self.room)]
        await session.start()
        await session.submit("look")

        let relaunched = GameSession(transport: StubTransport(), store: store)
        relaunched.restore()

        XCTAssertEqual(relaunched.blocks.map(\.text), session.blocks.map(\.text))
        XCTAssertEqual(relaunched.status, session.status)
        XCTAssertEqual(relaunched.mode, session.mode)
    }

    func testStartAfterARestoreDoesNotProbeBehindTheCover() async {
        transport.openResults = [.success(Self.room)]
        await session.start()

        let resumed = StubTransport()
        let relaunched = GameSession(transport: resumed, store: store)
        relaunched.restore()
        await relaunched.start()

        XCTAssertEqual(resumed.opens, 0, "The restored token still stands")
        XCTAssertEqual(resumed.probes, 0, "The saved run stays exact beneath the cover")

        relaunched.dismissLaunchOpener()
        await relaunched.resumeFromBackground()
        XCTAssertEqual(resumed.probes, 1, "A later foreground may check the visible run")
    }

    func testANonMutatingLocalProbeNeverPersistsASyntheticTurn() async {
        transport.openResults = [.success(Self.room)]
        await session.start()

        let localProbe = StubTransport()
        localProbe.probeCreatesTurn = false
        var pendingDuringProbe: PlayerTurn?
        localProbe.onProbe = {
            pendingDuringProbe = self.store.load()?.pendingTurn
        }
        let relaunched = GameSession(transport: localProbe, store: store)
        relaunched.restore()

        await relaunched.start()
        XCTAssertEqual(localProbe.probes, 0, "The launch cover keeps the run untouched")
        relaunched.dismissLaunchOpener()
        await relaunched.resumeFromBackground()

        XCTAssertEqual(localProbe.probes, 1)
        XCTAssertNil(pendingDuringProbe)
        XCTAssertEqual(relaunched.mode, .input)
    }

    func testForegroundCallbackBeforeStartLeavesTheInitialProbeToStart() async {
        transport.openResults = [.success(Self.room)]
        await session.start()

        let resumed = StubTransport()
        let relaunched = GameSession(transport: resumed, store: store, now: { self.clock.now })
        relaunched.restore()

        await relaunched.resumeFromBackground()
        XCTAssertEqual(resumed.probes, 0, "Nothing checks before launch has started")

        await relaunched.start()
        XCTAssertEqual(resumed.probes, 0, "The launch cover keeps the restored run untouched")

        relaunched.dismissLaunchOpener()
        await relaunched.resumeFromBackground()
        XCTAssertEqual(resumed.probes, 1)
    }

    func testBackgroundFlushesTransportCheckpoint() async {
        transport.openResults = [.success(Self.room)]
        await session.start()

        await session.prepareForBackground()

        XCTAssertEqual(transport.persists, 1)
    }

    func testForegroundCallbackBeforeStartCannotClearALostRunsEnding() async {
        transport.openResults = [.success(Self.room)]
        await session.start()

        let resumed = StubTransport()
        resumed.probeResults = [.failure(.lost("That thread has gone cold."))]
        resumed.openResults = [.success(Self.intro)]
        let relaunched = GameSession(transport: resumed, store: store, now: { self.clock.now })
        relaunched.restore()

        await relaunched.resumeFromBackground()
        await relaunched.start()

        XCTAssertEqual(resumed.probes, 0, "The run cannot be declared lost behind its cover")

        relaunched.dismissLaunchOpener()
        await relaunched.resumeFromBackground()

        XCTAssertEqual(resumed.probes, 1)
        XCTAssertEqual(resumed.opens, 0, "The narrated ending stays until the player taps")
        XCTAssertEqual(relaunched.mode, .ended)
        XCTAssertEqual(relaunched.blocks.last?.text, "That thread has gone cold.")
    }

    func testComingBackToAnExpiredRunSaysSoAndWaits() async {
        transport.openResults = [.success(Self.room)]
        await session.start()
        transport.probeResults = [.failure(.lost("That thread has gone cold."))]
        transport.openResults = [.success(Self.intro)]
        clock.now += 3600

        await session.resumeFromBackground()

        XCTAssertEqual(transport.probes, 1)
        XCTAssertEqual(transport.opens, 1, "The player reads the line before anything restarts")
        XCTAssertEqual(session.mode, .ended)
        XCTAssertEqual(session.blocks.last?.text, "That thread has gone cold.")
    }

    func testARunWaitingOnAKeypressIsNotProbed() async {
        // The probe is an empty command, and a run waiting on a key would read
        // it as the key and move on without the player.
        transport.openResults = [.success(Self.intro)]
        await session.start()
        clock.now += 3600

        await session.resumeFromBackground()

        XCTAssertEqual(transport.probes, 0)
        XCTAssertTrue(transport.sent.isEmpty)
    }

    func testAForegroundStraightAfterTheLastTurnDoesNotCheckAgain() async {
        // A cold launch runs start() and reaches .active together, and flicking
        // through the app switcher does the same. A run cannot expire in that
        // gap, so the check would only spend rate limit.
        transport.openResults = [.success(Self.room)]
        await session.start()

        await session.resumeFromBackground()

        XCTAssertEqual(transport.probes, 0)
    }

    func testAForegroundAfterALongAbsenceChecksTheRun() async {
        transport.openResults = [.success(Self.room)]
        await session.start()
        clock.now += 3600

        await session.resumeFromBackground()

        XCTAssertEqual(transport.probes, 1)
    }
}
