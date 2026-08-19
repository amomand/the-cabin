import SwiftUI

/// Health and fear, kept small and quiet above the prose.
///
/// The pocket notebook lives here too, but not as a button: a long press
/// anywhere on this strip opens it. A pencil glyph was the one thing on the
/// screen that looked like an app, and the notebook is a playtest tool, not
/// part of the room.
struct StatusLineView: View {
    let status: Status?
    let onOpenNotebook: () -> Void

    var body: some View {
        HStack(spacing: 20) {
            if let status {
                reading("health", status.health)
                reading("fear", status.fear)
            }
            Spacer(minLength: 0)
        }
        .font(Theme.statusFont)
        .padding(.horizontal, Theme.inset)
        .padding(.vertical, 10)
        .frame(maxWidth: .infinity, minHeight: 28, alignment: .leading)
        .contentShape(Rectangle())
        .background(Theme.background)
        .overlay(alignment: .bottom) {
            Rectangle()
                .fill(Theme.rule)
                .frame(height: 1)
        }
        .onLongPressGesture(minimumDuration: 0.4, perform: onOpenNotebook)
        .accessibilityElement(children: .ignore)
        .accessibilityLabel(accessibilityText)
        .accessibilityAction(named: "Open field notes", onOpenNotebook)
    }

    private var accessibilityText: String {
        guard let status else { return "No readings yet" }
        return "Health \(status.health), fear \(status.fear)"
    }

    private func reading(_ label: String, _ value: Int) -> some View {
        HStack(spacing: 6) {
            Text(label)
                .foregroundStyle(Theme.statusLabel)
                .tracking(0.8)
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
