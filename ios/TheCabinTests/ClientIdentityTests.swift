import XCTest
@testable import TheCabin

/// The identity keys durable saves on the server. If it ever changes under a
/// player, their saves are still on the server but no longer reachable, so the
/// only property that really matters is that it does not move.
final class ClientIdentityTests: XCTestCase {
    func testTheIdentityIsStableAcrossCalls() throws {
        guard let first = ClientIdentity.current() else {
            throw XCTSkip("No keychain available in this environment")
        }

        XCTAssertEqual(ClientIdentity.current(), first)
        XCTAssertEqual(ClientIdentity.current(), first)
    }

    func testTheIdentityIsShapedTheWayTheServerDemands() throws {
        guard let identity = ClientIdentity.current() else {
            throw XCTSkip("No keychain available in this environment")
        }

        // CLIENT_ID_PATTERN on the server: ^[A-Za-z0-9._-]{16,128}$
        let allowed = CharacterSet(charactersIn: "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789._-")
        XCTAssertTrue((16...128).contains(identity.count))
        XCTAssertTrue(identity.unicodeScalars.allSatisfy(allowed.contains))
    }
}
