import Darwin
import Foundation
import Security

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
        guard SecItemCopyMatching(query as CFDictionary, &item) == errSecSuccess,
              let data = item as? Data,
              let credential = String(data: data, encoding: .utf8)
        else { return nil }
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
        guard update == errSecItemNotFound else { return false }

        let item = query.merging(attributes) { _, new in new }
        return SecItemAdd(item as CFDictionary, nil) == errSecSuccess
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
            _ = store.save(injected)
            setProcessCredential(injected)
            return
        }
        if let stored = usable(store.load()) {
            setProcessCredential(stored)
        }
    }

    private static func usable(_ credential: String?) -> String? {
        guard let credential,
              !credential.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
        else { return nil }
        return credential
    }
}
