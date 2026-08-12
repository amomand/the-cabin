import SwiftUI

/// Health and fear, pinned above the transcript so they never scroll away.
struct StatusLineView: View {
    let status: Status

    var body: some View {
        HStack(spacing: 24) {
            reading("Health", status.health)
            reading("Fear", status.fear)
            Spacer()
        }
        .font(Theme.statusFont)
        .padding(.horizontal, 16)
        .padding(.vertical, 8)
        .background(Theme.background)
        .overlay(alignment: .bottom) {
            Rectangle()
                .fill(Theme.rule)
                .frame(height: 1)
        }
        .accessibilityElement(children: .combine)
        .accessibilityLabel("Health \(status.health), fear \(status.fear)")
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
