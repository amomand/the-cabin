import Foundation
import SwiftUI

/// A presentation-only cover for a restored run.
///
/// Its tap removes the cover. It never sends input or changes the run beneath
/// it; the real opening frame keeps its existing keypress path.
struct LaunchOpenerView: View {
    let lines: [String]
    let onDismiss: () -> Void

    private var blocks: [TranscriptBlock] {
        lines.enumerated().map { index, line in
            TranscriptBlock(
                id: Self.stableID(for: index),
                kind: .narration,
                text: line
            )
        }
    }

    var body: some View {
        VStack(spacing: 0) {
            TranscriptView(blocks: blocks)
                .frame(maxHeight: .infinity)

            WaitingCursor(isWorking: false)
        }
        .contentShape(Rectangle())
        .onTapGesture(perform: onDismiss)
        .accessibilityAction(.default, onDismiss)
    }

    /// Stable identities keep repeated rendering from making a transport-
    /// supplied opener look like a new transcript.
    private static func stableID(for index: Int) -> UUID {
        let suffix = String(format: "%012llX", UInt64(index))
        return UUID(uuidString: "B04C8434-94C7-4D26-AB7D-\(suffix)")!
    }
}
