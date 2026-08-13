import XCTest
@testable import TheCabin

private final class ScriptedURLProtocol: URLProtocol {
    static var handler: ((URLRequest) throws -> (HTTPURLResponse, Data))?

    override class func canInit(with request: URLRequest) -> Bool { true }
    override class func canonicalRequest(for request: URLRequest) -> URLRequest { request }

    override func startLoading() {
        guard let handler = Self.handler else {
            client?.urlProtocol(self, didFailWithError: URLError(.unknown))
            return
        }
        do {
            let (response, data) = try handler(request)
            client?.urlProtocol(self, didReceive: response, cacheStoragePolicy: .notAllowed)
            client?.urlProtocol(self, didLoad: data)
            client?.urlProtocolDidFinishLoading(self)
        } catch {
            client?.urlProtocol(self, didFailWithError: error)
        }
    }

    override func stopLoading() {}
}

@MainActor
final class ServerTransportTests: XCTestCase {
    private var session: URLSession!
    private var delays: [UInt64]!
    private var now: Date!

    override func setUp() {
        let configuration = URLSessionConfiguration.ephemeral
        configuration.protocolClasses = [ScriptedURLProtocol.self]
        session = URLSession(configuration: configuration)
        delays = []
        now = Date(timeIntervalSince1970: 1_000_000)
    }

    override func tearDown() {
        ScriptedURLProtocol.handler = nil
        session.invalidateAndCancel()
    }

    private func transport(clientID: String? = "client-identity-1234") -> ServerTransport {
        ServerTransport(
            baseURL: URL(string: "https://example.invalid")!,
            clientID: clientID,
            session: session,
            sleep: { delay in self.delays.append(delay) },
            now: { self.now }
        )
    }

    private func response(
        for request: URLRequest,
        status: Int = 200,
        json: String
    ) -> (HTTPURLResponse, Data) {
        (
            HTTPURLResponse(
                url: request.url!,
                statusCode: status,
                httpVersion: nil,
                headerFields: ["Content-Type": "application/json"]
            )!,
            Data(json.utf8)
        )
    }

    private func body(_ request: URLRequest) throws -> [String: Any] {
        let data: Data
        if let body = request.httpBody {
            data = body
        } else {
            let stream = try XCTUnwrap(request.httpBodyStream)
            stream.open()
            defer { stream.close() }
            var collected = Data()
            var buffer = [UInt8](repeating: 0, count: 4096)
            while true {
                let count = stream.read(&buffer, maxLength: buffer.count)
                guard count >= 0 else { throw stream.streamError ?? URLError(.cannotDecodeRawData) }
                if count == 0 { break }
                collected.append(buffer, count: count)
            }
            data = collected
        }
        return try XCTUnwrap(
            JSONSerialization.jsonObject(with: data)
                as? [String: Any]
        )
    }

    func testAmbiguousNetworkFailureRetriesTheSameTurnIDAndBody() async throws {
        var requests: [URLRequest] = []
        ScriptedURLProtocol.handler = { request in
            requests.append(request)
            if requests.count == 1 {
                throw URLError(.networkConnectionLost)
            }
            return self.response(
                for: request,
                json: #"{"type":"render","lines":["The room answers."],"prompt":"> "}"#
            )
        }
        let transport = transport()
        transport.adopt(resumeHandle: "token")

        let frame = try await transport.send(.input("look"))

        XCTAssertEqual(frame.lines, ["The room answers."])
        XCTAssertEqual(requests.count, 2)
        XCTAssertEqual(try body(requests[0])["turn_id"] as? Int, 1)
        XCTAssertEqual(try body(requests[1])["turn_id"] as? Int, 1)
        XCTAssertEqual(try body(requests[0])["text"] as? String, "look")
        XCTAssertEqual(try body(requests[1])["text"] as? String, "look")
        XCTAssertEqual(delays, [250_000_000])
    }

    func testDeadHostGivesUpInsideTheAttemptBound() async {
        var attempts = 0
        ScriptedURLProtocol.handler = { _ in
            attempts += 1
            throw URLError(.cannotFindHost)
        }
        let transport = transport()
        transport.adopt(resumeHandle: "token")

        do {
            _ = try await transport.send(.input("look"))
            XCTFail("The dead host should not be retried forever")
        } catch let failure as TransportFailure {
            XCTAssertEqual(failure, .unreachable)
        } catch {
            XCTFail("Unexpected error: \(error)")
        }

        XCTAssertEqual(attempts, 3)
        XCTAssertEqual(delays, [250_000_000, 250_000_000])
    }

    func testResumeHandleCarriesTheNextTurnIDAcrossRelaunch() async throws {
        var ids: [Int] = []
        ScriptedURLProtocol.handler = { request in
            ids.append(try XCTUnwrap(try self.body(request)["turn_id"] as? Int))
            return self.response(
                for: request,
                json: #"{"type":"render","lines":[],"prompt":"> "}"#
            )
        }
        let first = transport()
        first.adopt(resumeHandle: "legacy-token")
        _ = try await first.send(.input("look"))

        let resumed = transport()
        resumed.adopt(resumeHandle: try XCTUnwrap(first.resumeHandle))
        _ = try await resumed.send(.input("north"))

        XCTAssertEqual(ids, [1, 2])
    }

    func testBusyAndRateLimitUseDifferentBackoffs() async throws {
        var statuses = [409, 429, 200]
        ScriptedURLProtocol.handler = { request in
            let status = statuses.removeFirst()
            if status == 200 {
                return self.response(
                    for: request,
                    json: #"{"type":"render","lines":[],"prompt":"> "}"#
                )
            }
            return self.response(
                for: request,
                status: status,
                json: #"{"type":"error","message":"The room needs a moment to settle."}"#
            )
        }
        let transport = transport()
        transport.adopt(resumeHandle: "token")

        _ = try await transport.send(.input("look"))

        XCTAssertEqual(delays, [250_000_000, 1_000_000_000])
    }

    func testAUsedUpDeadlineDoesNotStartAnotherRequest() async {
        var attempts = 0
        ScriptedURLProtocol.handler = { _ in
            attempts += 1
            self.now += 45
            throw URLError(.networkConnectionLost)
        }
        let transport = transport()
        transport.adopt(resumeHandle: "token")

        do {
            _ = try await transport.send(.input("look"))
            XCTFail("The retry must stay inside the request budget")
        } catch let failure as TransportFailure {
            XCTAssertEqual(failure, .unreachable)
        } catch {
            XCTFail("Unexpected error: \(error)")
        }

        XCTAssertEqual(attempts, 1)
        XCTAssertTrue(delays.isEmpty)
    }

    func testDeadlineIsRecheckedAfterTheBackoffReturns() async {
        var attempts = 0
        var clock = Date(timeIntervalSince1970: 1_000_000)
        var postSleepReads: Int?
        ScriptedURLProtocol.handler = { request in
            attempts += 1
            if attempts == 1 {
                clock += 44.74
                throw URLError(.networkConnectionLost)
            }
            return self.response(
                for: request,
                json: #"{"type":"render","lines":[],"prompt":"> "}"#
            )
        }
        let transport = ServerTransport(
            baseURL: URL(string: "https://example.invalid")!,
            clientID: "client-identity-1234",
            session: session,
            sleep: { delay in
                clock += TimeInterval(delay) / 1_000_000_000
                postSleepReads = 0
            },
            now: {
                if let reads = postSleepReads {
                    if reads == 0 {
                        postSleepReads = 1
                    } else {
                        // Model scheduling just after waitBeforeRetry's final
                        // check but before the next URLSession task starts.
                        clock += 0.02
                        postSleepReads = nil
                    }
                }
                return clock
            }
        )
        transport.adopt(resumeHandle: "token")

        do {
            _ = try await transport.send(.input("look"))
            XCTFail("No request may begin after the overall deadline")
        } catch let failure as TransportFailure {
            XCTAssertEqual(failure, .unreachable)
        } catch {
            XCTFail("Unexpected error: \(error)")
        }

        XCTAssertEqual(attempts, 1)
    }

    func testAnAmbiguousAnonymousOpenIsNotRepeated() async {
        var attempts = 0
        ScriptedURLProtocol.handler = { _ in
            attempts += 1
            throw URLError(.networkConnectionLost)
        }
        let transport = transport(clientID: nil)

        do {
            _ = try await transport.open()
            XCTFail("An anonymous create has no identity with which to supersede a leak")
        } catch let failure as TransportFailure {
            XCTAssertEqual(failure, .unreachable)
        } catch {
            XCTFail("Unexpected error: \(error)")
        }

        XCTAssertEqual(attempts, 1)
    }
}
