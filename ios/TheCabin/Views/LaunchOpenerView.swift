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
                id: Self.stableIDs[index, default: UUID()],
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

    /// Stable identities keep a liveness probe behind the cover from making
    /// the visible opener look like a new transcript.
    private static let stableIDs = [
        UUID(uuidString: "B04C8434-94C7-4D26-AB7D-395545C2487B")!,
        UUID(uuidString: "F7D4257D-9136-4C55-AF91-9ADCCF78DF0B")!,
        UUID(uuidString: "80690304-B6DA-4805-97F4-EAAC18322B8E")!,
    ]
}

private extension Array {
    subscript(index: Index, default fallback: @autoclosure () -> Element) -> Element {
        indices.contains(index) ? self[index] : fallback()
    }
}
