import XCTest
@testable import TheCabin

private final class StubModelCredentialStore: ModelCredentialStoring {
    var stored: String?
    private(set) var loadCount = 0
    private(set) var saved: [String] = []

    init(stored: String? = nil) {
        self.stored = stored
    }

    func load() -> String? {
        loadCount += 1
        return stored
    }

    func save(_ credential: String) -> Bool {
        saved.append(credential)
        stored = credential
        return true
    }
}

final class ModelCredentialTests: XCTestCase {
    func testTheRunningTestHostCarriesTheOfflineMarker() {
        XCTAssertNotNil(
            ProcessInfo.processInfo.environment["XCTestConfigurationFilePath"]
        )
    }

    func testInjectedLaunchCredentialIsSavedForLaterLaunches() {
        let store = StubModelCredentialStore()
        var processCredential: String?

        ModelCredential.bootstrap(
            environment: ["OPENAI_API_KEY": "mobile-key"],
            store: store,
            setProcessCredential: { processCredential = $0 }
        )

        XCTAssertEqual(store.saved, ["mobile-key"])
        XCTAssertEqual(store.loadCount, 0)
        XCTAssertEqual(processCredential, "mobile-key")
    }

    func testUntetheredLaunchRestoresTheStoredCredential() {
        let store = StubModelCredentialStore(stored: "stored-key")
        var processCredential: String?

        ModelCredential.bootstrap(
            environment: [:],
            store: store,
            setProcessCredential: { processCredential = $0 }
        )

        XCTAssertEqual(store.saved, [])
        XCTAssertEqual(store.loadCount, 1)
        XCTAssertEqual(processCredential, "stored-key")
    }

    func testXCTestClearsTheCredentialWithoutReadingKeychain() {
        let store = StubModelCredentialStore(stored: "must-not-load")
        var observed: [String?] = []

        ModelCredential.bootstrap(
            environment: ["XCTestConfigurationFilePath": "/tmp/tests.xctestconfiguration"],
            store: store,
            setProcessCredential: { observed.append($0) }
        )

        XCTAssertEqual(store.saved, [])
        XCTAssertEqual(store.loadCount, 0)
        XCTAssertEqual(observed.count, 1)
        XCTAssertNil(observed[0])
    }

    func testBlankInjectedValueFallsBackToStoredCredential() {
        let store = StubModelCredentialStore(stored: "stored-key")
        var processCredential: String?

        ModelCredential.bootstrap(
            environment: ["OPENAI_API_KEY": "   "],
            store: store,
            setProcessCredential: { processCredential = $0 }
        )

        XCTAssertEqual(store.saved, [])
        XCTAssertEqual(processCredential, "stored-key")
    }
}
