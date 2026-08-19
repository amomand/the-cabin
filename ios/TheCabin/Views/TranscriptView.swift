import SwiftUI

/// The run so far, scrolling.
struct TranscriptView: View {
    let blocks: [TranscriptBlock]

    var body: some View {
        let roles = TranscriptRole.roles(for: blocks)
        ScrollViewReader { proxy in
            ScrollView {
                LazyVStack(alignment: .leading, spacing: 0) {
                    ForEach(Array(zip(blocks, roles)), id: \.0.id) { block, role in
                        line(block, role)
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

    @ViewBuilder
    private func line(_ block: TranscriptBlock, _ role: TranscriptRole) -> some View {
        switch role {
        case .gap:
            // A blank line from the turn core is spacing, and carries its
            // meaning in the gap, so it keeps a height rather than collapsing,
            // but a paragraph's worth, not a whole empty row of type.
            Color.clear.frame(height: Theme.paragraphGap)
        case .rule:
            Rectangle()
                .fill(Theme.rule)
                .frame(width: Theme.ruleWidth, height: 1)
                .padding(.top, 4)
                .padding(.bottom, 12)
                .accessibilityHidden(true)
        case .title:
            prose(block.text, font: Theme.titleFont, colour: Theme.title)
                .tracking(0.4)
                .padding(.top, 6)
                .accessibilityAddTraits(.isHeader)
        case .aside(let text):
            prose(text, font: Theme.asideFont, colour: Theme.aside)
        case .body:
            prose(block.text, font: Theme.font, colour: Theme.colour(for: block.kind))
        }
    }

    private func prose(_ text: String, font: Font, colour: Color) -> some View {
        Text(text)
            .font(font)
            .foregroundStyle(colour)
            .lineSpacing(Theme.leading)
            .textSelection(.enabled)
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(.vertical, 2)
    }
}
