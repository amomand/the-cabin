import SwiftUI

/// Health and fear, with the pocket notebook kept beside them.
struct StatusLineView: View {
    let status: Status?
    let onOpenNotebook: () -> Void

    var body: some View {
        HStack(spacing: 24) {
            if let status {
                HStack(spacing: 24) {
                    reading("Health", status.health)
                    reading("Fear", status.fear)
                }
                .accessibilityElement(children: .combine)
                .accessibilityLabel("Health \(status.health), fear \(status.fear)")
            }
            Spacer()
            Button(action: onOpenNotebook) {
                Image(systemName: "square.and.pencil")
                    .foregroundStyle(Theme.statusValue)
                    .frame(width: 44, height: 44)
                    .contentShape(Rectangle())
            }
            .buttonStyle(.plain)
            .accessibilityLabel("Open field notes")
        }
        .font(Theme.statusFont)
        .padding(.horizontal, Theme.inset)
        .padding(.vertical, 8)
        .background(Theme.background)
        .overlay(alignment: .bottom) {
            Rectangle()
                .fill(Theme.rule)
                .frame(height: 1)
        }
    }

    private func reading(_ label: String, _ value: Int) -> some View {
        HStack(spacing: 6) {
            Text(label)
                .foregroundStyle(Theme.statusLabel)
            Text("\(value)")
                .foregroundStyle(Theme.statusValue)
                .monospacedDigit()
                // The number moving is the only movement on this line, so it is
                // worth noticing.
                .contentTransition(.numericText())
                .animation(.easeOut(duration: 0.2), value: value)
        }
    }
}
