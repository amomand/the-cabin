import SwiftUI

/// One local notebook page. Its context was frozen before this sheet appeared.
struct PlaytestNoteSheet: View {
    @ObservedObject var session: GameSession
    @FocusState private var noteFocused: Bool
    @State private var saveFailed = false

    var body: some View {
        NavigationStack {
            VStack(alignment: .leading, spacing: 16) {
                if let context = session.playtestNoteDraft?.context {
                    contextView(context)
                }

                ZStack(alignment: .topLeading) {
                    TextEditor(text: noteBody)
                        .font(Theme.font)
                        .scrollContentBackground(.hidden)
                        .focused($noteFocused)

                    if (session.playtestNoteDraft?.body ?? "").isEmpty {
                        Text("What should you remember?")
                            .font(Theme.font)
                            .foregroundStyle(Theme.statusLabel)
                            .padding(.horizontal, 5)
                            .padding(.vertical, 8)
                            .allowsHitTesting(false)
                    }
                }
                .frame(minHeight: 160)
                .padding(8)
                .background(Theme.rule.opacity(0.45))
                .clipShape(RoundedRectangle(cornerRadius: 8))

                if saveFailed {
                    Text("The page won't take the ink.")
                        .font(Theme.statusFont)
                        .foregroundStyle(Theme.refusal)
                }
            }
            .padding(16)
            .background(Theme.background)
            .foregroundStyle(Theme.narration)
            .navigationTitle("Field note")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Close", action: session.cancelPlaytestNote)
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Keep", action: save)
                        .disabled(trimmedBody.isEmpty)
                }
                if let exportURL = session.playtestNotesExportURL {
                    ToolbarItem(placement: .bottomBar) {
                        ShareLink(item: exportURL) {
                            Label("Carry notes out", systemImage: "square.and.arrow.up")
                        }
                    }
                }
            }
        }
        .preferredColorScheme(.dark)
        .presentationDetents([.medium, .large])
        .presentationDragIndicator(.visible)
        .onAppear { noteFocused = true }
    }

    private var noteBody: Binding<String> {
        Binding(
            get: { session.playtestNoteDraft?.body ?? "" },
            set: {
                saveFailed = false
                session.updatePlaytestNote($0)
            }
        )
    }

    private var trimmedBody: String {
        (session.playtestNoteDraft?.body ?? "")
            .trimmingCharacters(in: .whitespacesAndNewlines)
    }

    private func save() {
        saveFailed = !session.savePlaytestNote()
    }

    @ViewBuilder
    private func contextView(_ context: PlaytestNoteContext) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            if let status = context.status {
                HStack(spacing: 12) {
                    Text("Health \(status.health)")
                    Text("Fear \(status.fear)")
                }
                .font(Theme.statusFont)
                .foregroundStyle(Theme.statusValue)
            }

            ForEach(
                Array(context.recentTranscript.suffix(3).enumerated()),
                id: \.offset
            ) { _, line in
                Text(line.text.isEmpty ? " " : line.text)
                    .font(Theme.font)
                    .foregroundStyle(Theme.colour(for: line.kind))
                    .lineLimit(2)
            }
        }
        .accessibilityElement(children: .combine)
    }
}
