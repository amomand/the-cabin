import SwiftUI

/// The run so far, scrolling.
struct TranscriptView: View {
    let blocks: [TranscriptBlock]

    var body: some View {
        ScrollViewReader { proxy in
            ScrollView {
                LazyVStack(alignment: .leading, spacing: 0) {
                    ForEach(blocks) { block in
                        line(block)
                            .id(block.id)
                    }
                    // An anchor of its own, so scrolling to the end does not
                    // depend on the height of the last block.
                    Color.clear
                        .frame(height: 1)
                        .id(Self.bottomAnchor)
                }
                .padding(.horizontal, Theme.inset)
                .padding(.vertical, 12)
                .frame(maxWidth: .infinity, alignment: .leading)
            }
            .scrollDismissesKeyboard(.interactively)
            .onChange(of: blocks.last?.id) {
                withAnimation(.easeOut(duration: 0.2)) {
                    proxy.scrollTo(Self.bottomAnchor, anchor: .bottom)
                }
            }
            .onAppear {
                proxy.scrollTo(Self.bottomAnchor, anchor: .bottom)
            }
        }
    }

    private static let bottomAnchor = "transcript-bottom"

    private func line(_ block: TranscriptBlock) -> some View {
        // A blank line from the turn core is spacing, and carries its meaning
        // in the gap, so it keeps its height rather than collapsing.
        Text(block.text.isEmpty ? " " : block.text)
            .font(Theme.font)
            .foregroundStyle(Theme.colour(for: block.kind))
            .textSelection(.enabled)
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(.vertical, 2)
    }
}
