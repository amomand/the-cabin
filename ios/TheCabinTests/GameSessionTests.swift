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
    private var transport: StubTransport!
    private var clock: TestClock!
    private var session: GameSession!

    override func setUpWithError() throws {
        directory = URL(fileURLWithPath: NSTemporaryDirectory())
            .appendingPathComponent(UUID().uuidString)
        store = TranscriptStore(directory: directory)
        transport = StubTransport()
        let clock = TestClock()
        self.clock = clock
        session = GameSession(transport: transport, store: store, now: { clock.now })
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

    func testARefusalIsNarratedAndTheRunCarriesOn() async {
        transport.openResults = [.success(Self.room)]
        transport.sendResults = [.failure(.busy("The room needs a moment to settle."))]
        await session.start()

        await session.submit("look")

        XCTAssertEqual(session.blocks.last?.text, "The room needs a moment to settle.")
        XCTAssertEqual(session.blocks.last?.kind, .refusal)
        XCTAssertEqual(session.mode, .input, "A busy room is still there to be asked again")
        XCTAssertEqual(transport.opens, 1, "Nothing was lost, so nothing should be reopened")
    }

    func testAnUnreachableServerIsNarratedInTheWorldsVoice() async {
        transport.openResults = [.success(Self.room)]
        transport.sendResults = [.failure(.unreachable)]
        await session.start()

        await session.submit("look")

        XCTAssertEqual(session.blocks.last?.text, Narration.unreachable)
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
        await session.start()
        transport.cancelNextSend = true

        await session.submit("look")

        // The echo is the player's own, but the room must not be made to
        // answer a question that was never finished being asked.
        XCTAssertEqual(session.blocks.map(\.text), ["The door hangs open.", "> look"])
        XCTAssertEqual(session.mode, .input)
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

    func testStartAfterARestoreProbesRatherThanOpeningAgain() async {
        transport.openResults = [.success(Self.room)]
        await session.start()

        let resumed = StubTransport()
        let relaunched = GameSession(transport: resumed, store: store)
        relaunched.restore()
        await relaunched.start()

        XCTAssertEqual(resumed.opens, 0, "The restored token still stands")
        XCTAssertEqual(resumed.probes, 1)
    }

    func testForegroundCallbackBeforeStartLeavesTheInitialProbeToStart() async {
        transport.openResults = [.success(Self.room)]
        await session.start()

        let resumed = StubTransport()
        let relaunched = GameSession(transport: resumed, store: store, now: { self.clock.now })
        relaunched.restore()

        await relaunched.resumeFromBackground()
        XCTAssertEqual(resumed.probes, 0, "The launch task owns the first liveness check")

        await relaunched.start()
        XCTAssertEqual(resumed.probes, 1)
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
