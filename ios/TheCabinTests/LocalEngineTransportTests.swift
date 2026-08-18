import XCTest
@testable import TheCabin

private final class StubPythonDispatcher: PythonDispatching {
    var responses: [String] = []
    private(set) var requests: [[String: Any]] = []

    func dispatch(_ request: Data) async throws -> Data {
        let object = try JSONSerialization.jsonObject(with: request)
        requests.append(try XCTUnwrap(object as? [String: Any]))
        guard !responses.isEmpty else { throw TransportFailure.unreachable }
        return Data(responses.removeFirst().utf8)
    }
}

@MainActor
final class LocalEngineTransportTests: XCTestCase {
    private static let firstHandle =
        #"{"next_turn_id":1,"run_id":"runone","version":1}"#
    private static let secondHandle =
        #"{"next_turn_id":2,"run_id":"runone","version":1}"#

    func testOpenMapsPythonFrameAndStoresOpaqueHandle() async throws {
        let dispatcher = StubPythonDispatcher()
        dispatcher.responses = [
            #"{"ok":true,"frame":{"type":"render","lines":["It waits."],"clear":true,"wait_for_key":true},"resume_handle":"{\"next_turn_id\":1,\"run_id\":\"runone\",\"version\":1}"}"#
        ]
        let transport = LocalEngineTransport(dispatcher: dispatcher)

        let frame = try await transport.open()

        XCTAssertEqual(
            frame,
            RenderFrame(lines: ["It waits."], clear: true, waitForKey: true)
        )
        XCTAssertEqual(transport.resumeHandle, Self.firstHandle)
        XCTAssertEqual(dispatcher.requests.first?["operation"] as? String, "open")
    }

    func testMalformedOpenDoesNotAdoptResumeHandle() async {
        let dispatcher = StubPythonDispatcher()
        dispatcher.responses = [
            #"{"ok":true,"resume_handle":"{\"next_turn_id\":1,\"run_id\":\"runone\",\"version\":1}"}"#
        ]
        let transport = LocalEngineTransport(dispatcher: dispatcher)

        do {
            _ = try await transport.open()
            XCTFail("Expected a response without a frame to be rejected")
        } catch let failure as TransportFailure {
            XCTAssertEqual(failure, .malformed)
        } catch {
            XCTFail("Unexpected error: \(error)")
        }

        XCTAssertNil(transport.resumeHandle)
    }

    func testOpenRejectsAHandleThatStartsPastTheFirstTurn() async {
        let dispatcher = StubPythonDispatcher()
        dispatcher.responses = [
            #"{"ok":true,"frame":{"type":"render","lines":["It waits."]},"resume_handle":"{\"next_turn_id\":2,\"run_id\":\"runone\",\"version\":1}"}"#
        ]
        let transport = LocalEngineTransport(dispatcher: dispatcher)

        do {
            _ = try await transport.open()
            XCTFail("Expected an impossible opening sequence to be rejected")
        } catch let failure as TransportFailure {
            XCTAssertEqual(failure, .malformed)
        } catch {
            XCTFail("Unexpected error: \(error)")
        }

        XCTAssertNil(transport.resumeHandle)
    }

    func testSendSerializesTheNativeTurnAndAcceptsPythonSequence() async throws {
        let dispatcher = StubPythonDispatcher()
        dispatcher.responses = [
            #"{"ok":true,"resume_handle":"{\"next_turn_id\":1,\"run_id\":\"runone\",\"version\":1}"}"#,
            #"{"ok":true,"frame":{"type":"render","lines":["The trees keep still."],"prompt":"> "},"resume_handle":"{\"next_turn_id\":2,\"run_id\":\"runone\",\"version\":1}"}"#,
        ]
        let transport = LocalEngineTransport(dispatcher: dispatcher)
        transport.adopt(resumeHandle: Self.firstHandle)

        let frame = try await transport.send(.input("look"))

        XCTAssertEqual(frame.lines, ["The trees keep still."])
        XCTAssertEqual(transport.resumeHandle, Self.secondHandle)
        XCTAssertEqual(dispatcher.requests[0]["operation"] as? String, "adopt")
        XCTAssertEqual(dispatcher.requests[1]["turn_id"] as? Int, 1)
        let turn = try XCTUnwrap(dispatcher.requests[1]["turn"] as? [String: Any])
        XCTAssertEqual(turn["type"] as? String, "input")
        XCTAssertEqual(turn["text"] as? String, "look")
    }

    func testIncompleteSendKeepsTheReplayHandleAndTurnID() async throws {
        let dispatcher = StubPythonDispatcher()
        dispatcher.responses = [
            #"{"ok":true,"resume_handle":"{\"next_turn_id\":1,\"run_id\":\"runone\",\"version\":1}"}"#,
            #"{"ok":true,"resume_handle":"{\"next_turn_id\":2,\"run_id\":\"runone\",\"version\":1}"}"#,
            #"{"ok":true,"frame":{"type":"render","lines":["Already answered."],"prompt":"> "},"resume_handle":"{\"next_turn_id\":2,\"run_id\":\"runone\",\"version\":1}"}"#,
        ]
        let transport = LocalEngineTransport(dispatcher: dispatcher)
        transport.adopt(resumeHandle: Self.firstHandle)

        do {
            _ = try await transport.send(.input("look"))
            XCTFail("Expected a response without a frame to be rejected")
        } catch let failure as TransportFailure {
            XCTAssertEqual(failure, .malformed)
        } catch {
            XCTFail("Unexpected error: \(error)")
        }

        XCTAssertEqual(transport.resumeHandle, Self.firstHandle)
        let replayed = try await transport.send(.input("look"))

        XCTAssertEqual(replayed.lines, ["Already answered."])
        XCTAssertEqual(dispatcher.requests[1]["turn_id"] as? Int, 1)
        XCTAssertEqual(dispatcher.requests[2]["turn_id"] as? Int, 1)
        XCTAssertEqual(transport.resumeHandle, Self.secondHandle)
    }

    func testSendRejectsAHandleForAnotherRunWithoutCommittingIt() async {
        let dispatcher = StubPythonDispatcher()
        dispatcher.responses = [
            #"{"ok":true,"resume_handle":"{\"next_turn_id\":1,\"run_id\":\"runone\",\"version\":1}"}"#,
            #"{"ok":true,"frame":{"type":"render","lines":["Wrong run."]},"resume_handle":"{\"next_turn_id\":2,\"run_id\":\"runtwo\",\"version\":1}"}"#,
        ]
        let transport = LocalEngineTransport(dispatcher: dispatcher)
        transport.adopt(resumeHandle: Self.firstHandle)

        do {
            _ = try await transport.send(.input("look"))
            XCTFail("Expected a response from another run to be rejected")
        } catch let failure as TransportFailure {
            XCTAssertEqual(failure, .malformed)
        } catch {
            XCTFail("Unexpected error: \(error)")
        }

        XCTAssertEqual(transport.resumeHandle, Self.firstHandle)
    }

    func testSendRejectsAStaleSequenceWithoutCommittingIt() async {
        let dispatcher = StubPythonDispatcher()
        dispatcher.responses = [
            #"{"ok":true,"resume_handle":"{\"next_turn_id\":1,\"run_id\":\"runone\",\"version\":1}"}"#,
            #"{"ok":true,"frame":{"type":"render","lines":["Stale."]},"resume_handle":"{\"next_turn_id\":1,\"run_id\":\"runone\",\"version\":1}"}"#,
        ]
        let transport = LocalEngineTransport(dispatcher: dispatcher)
        transport.adopt(resumeHandle: Self.firstHandle)

        do {
            _ = try await transport.send(.input("look"))
            XCTFail("Expected a stale sequence to be rejected")
        } catch let failure as TransportFailure {
            XCTAssertEqual(failure, .malformed)
        } catch {
            XCTFail("Unexpected error: \(error)")
        }

        XCTAssertEqual(transport.resumeHandle, Self.firstHandle)
    }

    func testInvalidPersistedHandlesFailClosedWithoutDispatching() async {
        let invalidHandles = [
            "legacy-server-token",
            #"{"next_turn_id":0,"run_id":"runone","version":1}"#,
            #"{"next_turn_id":\#(Int.max),"run_id":"runone","version":1}"#,
            #"{"next_turn_id":1,"run_id":"run-one","version":1}"#,
        ]

        for invalidHandle in invalidHandles {
            let dispatcher = StubPythonDispatcher()
            let transport = LocalEngineTransport(dispatcher: dispatcher)
            transport.adopt(resumeHandle: invalidHandle)

            do {
                _ = try await transport.send(.input("look"))
                XCTFail("Expected an invalid persisted handle to lose the run")
            } catch let failure as TransportFailure {
                XCTAssertEqual(failure, .lost(Narration.threadGoneCold))
            } catch {
                XCTFail("Unexpected error: \(error)")
            }

            XCTAssertNil(transport.resumeHandle)
            XCTAssertTrue(dispatcher.requests.isEmpty)
        }
    }

    func testAdoptDoesNotSkipTheCrashWindowReplayID() async throws {
        let dispatcher = StubPythonDispatcher()
        dispatcher.responses = [
            #"{"ok":true,"resume_handle":"{\"next_turn_id\":2,\"run_id\":\"runone\",\"version\":1}"}"#,
            #"{"ok":true,"frame":{"type":"render","lines":["Already answered."],"prompt":"> "},"resume_handle":"{\"next_turn_id\":2,\"run_id\":\"runone\",\"version\":1}"}"#,
        ]
        let transport = LocalEngineTransport(dispatcher: dispatcher)
        transport.adopt(resumeHandle: Self.firstHandle)

        _ = try await transport.send(.keypress)

        XCTAssertEqual(
            dispatcher.requests[1]["turn_id"] as? Int,
            1,
            "Python may be ahead only because Swift still owes this replay"
        )
    }

    func testMismatchedReplayLosesTheUnsafeRun() async {
        let dispatcher = StubPythonDispatcher()
        dispatcher.responses = [
            #"{"ok":true,"resume_handle":"{\"next_turn_id\":1,\"run_id\":\"runone\",\"version\":1}"}"#,
            #"{"ok":false,"kind":"mismatch","message":"turn id was already used"}"#,
        ]
        let transport = LocalEngineTransport(dispatcher: dispatcher)
        transport.adopt(resumeHandle: Self.firstHandle)

        do {
            _ = try await transport.send(.keypress)
            XCTFail("Expected the unsafe run to fail closed")
        } catch let failure as TransportFailure {
            XCTAssertEqual(failure, .lost(Narration.threadGoneCold))
        } catch {
            XCTFail("Unexpected error: \(error)")
        }
        XCTAssertNil(transport.resumeHandle)
    }

    func testFailedBackgroundAdoptionPreservesHandleForVisibleRecovery() async {
        let dispatcher = StubPythonDispatcher()
        dispatcher.responses = [
            #"{"ok":false,"kind":"lost","message":"checkpoint missing"}"#,
            #"{"ok":false,"kind":"lost","message":"checkpoint missing"}"#,
        ]
        let transport = LocalEngineTransport(dispatcher: dispatcher)
        transport.adopt(resumeHandle: Self.firstHandle)

        await transport.persist()

        XCTAssertEqual(transport.resumeHandle, Self.firstHandle)
        do {
            try await transport.probe()
            XCTFail("Expected the foreground check to surface the lost run")
        } catch let failure as TransportFailure {
            XCTAssertEqual(failure, .lost(Narration.threadGoneCold))
        } catch {
            XCTFail("Unexpected error: \(error)")
        }
        XCTAssertNil(transport.resumeHandle)
        XCTAssertEqual(
            dispatcher.requests.compactMap { $0["operation"] as? String },
            ["adopt", "adopt"]
        )
    }

    func testGameOverDropsSwiftHandleAfterFrameDelivery() async throws {
        let dispatcher = StubPythonDispatcher()
        dispatcher.responses = [
            #"{"ok":true,"resume_handle":"{\"next_turn_id\":1,\"run_id\":\"runone\",\"version\":1}"}"#,
            #"{"ok":true,"frame":{"type":"render","lines":["The cold closes."],"game_over":true},"resume_handle":"{\"next_turn_id\":2,\"run_id\":\"runone\",\"version\":1}"}"#,
        ]
        let transport = LocalEngineTransport(dispatcher: dispatcher)
        transport.adopt(resumeHandle: Self.firstHandle)

        let frame = try await transport.send(.input("quit"))

        XCTAssertTrue(frame.gameOver)
        XCTAssertNil(transport.resumeHandle)
    }
}
