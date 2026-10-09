import XCTest
@testable import TheCabin

private final class StubModelCredentialStore: ModelCredentialStoring {
    var stored: [String: String]
    private(set) var loadCount = 0
    private(set) var saved: [(key: String, credential: String)] = []

    init(stored: [String: String] = [:]) {
        self.stored = stored
    }

    func load(_ key: String) -> String? {
        loadCount += 1
        return stored[key]
    }

    func save(_ credential: String, for key: String) -> Bool {
        saved.append((key: key, credential: credential))
        stored[key] = credential
        return true
    }
}

final class ModelCredentialTests: XCTestCase {
    private func bootstrap(
        environment: [String: String],
        store: StubModelCredentialStore
    ) -> [String: String?] {
        var process: [String: String?] = [:]
        ModelCredential.bootstrap(
            environment: environment,
            store: store,
            setProcessCredential: { key, credential in process[key] = credential }
        )
        return process
    }

    func testTheRunningTestHostCarriesTheOfflineMarker() {
        XCTAssertNotNil(
            ProcessInfo.processInfo.environment["XCTestConfigurationFilePath"]
        )
    }

    func testInjectedLaunchCredentialIsSavedForLaterLaunches() {
        let store = StubModelCredentialStore()

        let process = bootstrap(environment: ["ANTHROPIC_API_KEY": "mobile-key"], store: store)

        XCTAssertEqual(store.saved.map(\.key), ["ANTHROPIC_API_KEY"])
        XCTAssertEqual(store.saved.map(\.credential), ["mobile-key"])
        XCTAssertEqual(process["ANTHROPIC_API_KEY"], "mobile-key")
        XCTAssertNil(process["OPENAI_API_KEY"] ?? nil)
    }

    func testUntetheredLaunchRestoresEachStoredCredential() {
        let store = StubModelCredentialStore(stored: [
            "ANTHROPIC_API_KEY": "stored-anthropic",
            "OPENAI_API_KEY": "stored-openai",
        ])

        let process = bootstrap(environment: [:], store: store)

        XCTAssertTrue(store.saved.isEmpty)
        XCTAssertEqual(store.loadCount, 2)
        XCTAssertEqual(process["ANTHROPIC_API_KEY"], "stored-anthropic")
        XCTAssertEqual(process["OPENAI_API_KEY"], "stored-openai")
    }

    func testXCTestClearsEveryCredentialWithoutReadingKeychain() {
        let store = StubModelCredentialStore(stored: ["OPENAI_API_KEY": "must-not-load"])
        var observed: [String: String?] = [:]

        ModelCredential.bootstrap(
            environment: ["XCTestConfigurationFilePath": "/tmp/tests.xctestconfiguration"],
            store: store,
            setProcessCredential: { key, credential in observed[key] = credential }
        )

        XCTAssertTrue(store.saved.isEmpty)
        XCTAssertEqual(store.loadCount, 0)
        XCTAssertEqual(Set(observed.keys), Set(ModelCredential.keys))
        XCTAssertTrue(observed.values.allSatisfy { $0 == nil })
    }

    func testBlankInjectedValueFallsBackToStoredCredential() {
        let store = StubModelCredentialStore(stored: ["ANTHROPIC_API_KEY": "stored-key"])

        let process = bootstrap(environment: ["ANTHROPIC_API_KEY": "   "], store: store)

        XCTAssertTrue(store.saved.isEmpty)
        XCTAssertEqual(process["ANTHROPIC_API_KEY"], "stored-key")
    }

    func testOneProviderKeyDoesNotDisturbTheOther() {
        let store = StubModelCredentialStore(stored: ["OPENAI_API_KEY": "stored-openai"])

        let process = bootstrap(environment: ["ANTHROPIC_API_KEY": "fresh-anthropic"], store: store)

        XCTAssertEqual(process["ANTHROPIC_API_KEY"], "fresh-anthropic")
        XCTAssertEqual(process["OPENAI_API_KEY"], "stored-openai")
        XCTAssertEqual(store.stored["OPENAI_API_KEY"], "stored-openai")
    }
}
