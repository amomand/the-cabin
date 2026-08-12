import Foundation
import Security

/// The stable identity that keys durable saves on the server.
///
/// It is a bearer secret: anyone holding it can read and overwrite those saves,
/// so it lives in the keychain rather than in defaults or the transcript file,
/// and it is generated once per install and never sent anywhere but the session
/// endpoint.
enum ClientIdentity {
    private static let service = "uk.co.amomand.thecabin.clientID"
    private static let account = "durable-saves"

    /// The identity for this install, minting one on first use.
    ///
    /// Returns nil only if the keychain refuses both reads and writes, in which
    /// case the app plays on without durable saves rather than failing to start.
    static func current() -> String? {
        if let existing = load() { return existing }
        let minted = mint()
        return store(minted) ? minted : nil
    }

    /// 32 random bytes in base64url, which is 43 characters drawn from the
    /// charset the server accepts and comfortably inside its 16–128 bound.
    private static func mint() -> String {
        var bytes = [UInt8](repeating: 0, count: 32)
        if SecRandomCopyBytes(kSecRandomDefault, bytes.count, &bytes) != errSecSuccess {
            // The system generator does not fail in practice; if it ever does,
            // UUIDs still give an unguessable identity within the charset.
            return (UUID().uuidString + UUID().uuidString).replacingOccurrences(of: "-", with: "")
        }
        return Data(bytes).base64EncodedString()
            .replacingOccurrences(of: "+", with: "-")
            .replacingOccurrences(of: "/", with: "_")
            .replacingOccurrences(of: "=", with: "")
    }

    private static func load() -> String? {
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
              let identity = String(data: data, encoding: .utf8)
        else { return nil }
        return identity
    }

    private static func store(_ identity: String) -> Bool {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account,
            kSecValueData as String: Data(identity.utf8),
            // Saves are only ever read while the player is playing, and the
            // identity should not follow the phone to a restore of a backup.
            kSecAttrAccessible as String: kSecAttrAccessibleWhenUnlockedThisDeviceOnly,
        ]
        let status = SecItemAdd(query as CFDictionary, nil)
        return status == errSecSuccess || status == errSecDuplicateItem
    }
}
