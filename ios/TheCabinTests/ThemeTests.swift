import UIKit
import XCTest
@testable import TheCabin

final class ThemeTests: XCTestCase {
    func testTheWebsBookFontExistsOnIOS() {
        XCTAssertNotNil(UIFont(name: Theme.bookFontName, size: 17))
    }
}
