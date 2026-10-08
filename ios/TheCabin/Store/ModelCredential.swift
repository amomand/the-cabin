import Darwin
import Foundation
import OSLog
import Security

/// Boot diagnostics for the model credentials. Logs which source supplied each
/// key and the Keychain status codes; never a credential itself.
private let credentialLog = Logger(
    subsystem: "uk.co.amomand.thecabin",
    category: "model-credential"
)

protocol ModelCredentialStoring {
    func load(_ key: String) -> String?
    @discardableResult func save(_ credential: String, for key: String) -> Bool
}

struct KeychainModelCredentialStore: ModelCredentialStoring {
    private let service = "uk.co.amomand.thecabin.modelCredential"
    // One Keychain item per provider key. The OpenAI account name predates
    // the Anthropic one, so an install that stored a key before the provider
    // switch keeps it.
    private static let accounts: [String: String] = [
        "ANTHROPIC_API_KEY": "anthropic-api-key",
        "OPENAI_API_KEY": "openai-api-key",
    ]

    private func account(for key: String) -> String {
        Self.accounts[key] ?? key.lowercased().replacingOccurrences(of: "_", with: "-")
    }

    func load(_ key: String) -> String? {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account(for: key),
            kSecReturnData as String: true,
            kSecMatchLimit as String: kSecMatchLimitOne,
        ]
        var item: CFTypeRef?
        let status = SecItemCopyMatching(query as CFDictionary, &item)
        guard status == errSecSuccess else {
            // An empty Keychain is the normal state of a fresh install, not a
            // failure; the boot log already says when no credential was found.
            if status != errSecItemNotFound {
                credentialLog.notice("keychain load failed for \(key, privacy: .public): OSStatus \(status, privacy: .public)")
            }
            return nil
        }
        guard let data = item as? Data,
              let credential = String(data: data, encoding: .utf8)
        else {
            credentialLog.notice("keychain load returned undecodable data for \(key, privacy: .public)")
            return nil
        }
        return credential
    }

    @discardableResult
    func save(_ credential: String, for key: String) -> Bool {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account(for: key),
        ]
        let attributes: [String: Any] = [
            kSecValueData as String: Data(credential.utf8),
            kSecAttrAccessible as String: kSecAttrAccessibleWhenUnlockedThisDeviceOnly,
        ]
        let update = SecItemUpdate(query as CFDictionary, attributes as CFDictionary)
        if update == errSecSuccess { return true }
        guard update == errSecItemNotFound else {
            credentialLog.notice("keychain update failed for \(key, privacy: .public): OSStatus \(update, privacy: .public)")
            return false
        }

        let item = query.merging(attributes) { _, new in new }
        let add = SecItemAdd(item as CFDictionary, nil)
        if add != errSecSuccess {
            credentialLog.notice("keychain add failed for \(key, privacy: .public): OSStatus \(add, privacy: .public)")
        }
        return add == errSecSuccess
    }
}

enum ModelCredential {
    /// Every key the embedded interpreter can use. The provider it actually
    /// calls is chosen by the engine's configuration; each key is handled on
    /// its own so a stored key for one provider survives a switch to the other.
    static let keys = ["ANTHROPIC_API_KEY", "OPENAI_API_KEY"]
    private static let testMarker = "XCTestConfigurationFilePath"

    static func bootstrap(
        environment: [String: String] = ProcessInfo.processInfo.environment,
        store: ModelCredentialStoring = KeychainModelCredentialStore(),
        setProcessCredential: (String, String?) -> Void = { key, credential in
            if let credential {
                setenv(key, credential, 1)
            } else {
                unsetenv(key)
            }
        }
    ) {
        if environment[testMarker] != nil {
            for key in keys {
                setProcessCredential(key, nil)
            }
            return
        }

        for key in keys {
            bootstrap(key: key, environment: environment, store: store, setProcessCredential: setProcessCredential)
        }
    }

    private static func bootstrap(
        key: String,
        environment: [String: String],
        store: ModelCredentialStoring,
        setProcessCredential: (String, String?) -> Void
    ) {
        if let injected = usable(environment[key]) {
            let saved = store.save(injected, for: key)
            credentialLog.notice(
                "\(key, privacy: .public) from launch environment (\(injected.count, privacy: .public) chars); keychain save \(saved ? "ok" : "failed", privacy: .public)"
            )
            setProcessCredential(key, injected)
            return
        }
        let envState = environment[key] == nil ? "absent" : "blank"
        if let stored = usable(store.load(key)) {
            credentialLog.notice(
                "\(key, privacy: .public) restored from keychain (\(stored.count, privacy: .public) chars); launch env \(envState, privacy: .public)"
            )
            setProcessCredential(key, stored)
            return
        }
        credentialLog.notice(
            "no \(key, privacy: .public): launch env \(envState, privacy: .public), keychain empty"
        )
    }

    private static func usable(_ credential: String?) -> String? {
        guard let credential,
              !credential.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
        else { return nil }
        return credential
    }
}
