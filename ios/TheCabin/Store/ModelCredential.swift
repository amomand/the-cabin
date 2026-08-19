import Darwin
import Foundation
import OSLog
import Security

/// Boot diagnostics for the model credential. Logs which source supplied the
/// key and the Keychain status codes; never the credential itself.
private let credentialLog = Logger(
    subsystem: "uk.co.amomand.thecabin",
    category: "model-credential"
)

protocol ModelCredentialStoring {
    func load() -> String?
    @discardableResult func save(_ credential: String) -> Bool
}

struct KeychainModelCredentialStore: ModelCredentialStoring {
    private let service = "uk.co.amomand.thecabin.modelCredential"
    private let account = "openai-api-key"

    func load() -> String? {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account,
            kSecReturnData as String: true,
            kSecMatchLimit as String: kSecMatchLimitOne,
        ]
        var item: CFTypeRef?
        let status = SecItemCopyMatching(query as CFDictionary, &item)
        guard status == errSecSuccess else {
            // An empty Keychain is the normal state of a fresh install, not a
            // failure; the boot log already says when no credential was found.
            if status != errSecItemNotFound {
                credentialLog.notice("keychain load failed: OSStatus \(status, privacy: .public)")
            }
            return nil
        }
        guard let data = item as? Data,
              let credential = String(data: data, encoding: .utf8)
        else {
            credentialLog.notice("keychain load returned undecodable data")
            return nil
        }
        return credential
    }

    @discardableResult
    func save(_ credential: String) -> Bool {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account,
        ]
        let attributes: [String: Any] = [
            kSecValueData as String: Data(credential.utf8),
            kSecAttrAccessible as String: kSecAttrAccessibleWhenUnlockedThisDeviceOnly,
        ]
        let update = SecItemUpdate(query as CFDictionary, attributes as CFDictionary)
        if update == errSecSuccess { return true }
        guard update == errSecItemNotFound else {
            credentialLog.notice("keychain update failed: OSStatus \(update, privacy: .public)")
            return false
        }

        let item = query.merging(attributes) { _, new in new }
        let add = SecItemAdd(item as CFDictionary, nil)
        if add != errSecSuccess {
            credentialLog.notice("keychain add failed: OSStatus \(add, privacy: .public)")
        }
        return add == errSecSuccess
    }
}

enum ModelCredential {
    private static let key = "OPENAI_API_KEY"
    private static let testMarker = "XCTestConfigurationFilePath"

    static func bootstrap(
        environment: [String: String] = ProcessInfo.processInfo.environment,
        store: ModelCredentialStoring = KeychainModelCredentialStore(),
        setProcessCredential: (String?) -> Void = { credential in
            if let credential {
                setenv(key, credential, 1)
            } else {
                unsetenv(key)
            }
        }
    ) {
        if environment[testMarker] != nil {
            setProcessCredential(nil)
            return
        }

        if let injected = usable(environment[key]) {
            let saved = store.save(injected)
            credentialLog.notice(
                "credential from launch environment (\(injected.count, privacy: .public) chars); keychain save \(saved ? "ok" : "failed", privacy: .public)"
            )
            setProcessCredential(injected)
            return
        }
        let envState = environment[key] == nil ? "absent" : "blank"
        if let stored = usable(store.load()) {
            credentialLog.notice(
                "credential restored from keychain (\(stored.count, privacy: .public) chars); launch env \(envState, privacy: .public)"
            )
            setProcessCredential(stored)
            return
        }
        credentialLog.notice(
            "no model credential: launch env \(envState, privacy: .public), keychain empty; free-text turns will use the offline fallback"
        )
    }

    private static func usable(_ credential: String?) -> String? {
        guard let credential,
              !credential.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
        else { return nil }
        return credential
    }
}
