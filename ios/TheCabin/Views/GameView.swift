import SwiftUI

/// The whole screen: status above, transcript in the middle, input below.
struct GameView: View {
    @ObservedObject var session: GameSession
    @State private var draft = ""
    @FocusState private var inputFocused: Bool

    var body: some View {
        VStack(spacing: 0) {
            if let status = session.status {
                StatusLineView(status: status)
                    .transition(.opacity)
            }

            TranscriptView(blocks: session.blocks)
                .frame(maxHeight: .infinity)
                .contentShape(Rectangle())
                .onTapGesture { tapped() }

            if session.mode == .input {
                InputBar(
                    prompt: session.prompt ?? "> ",
                    isWorking: session.isWorking,
                    draft: $draft,
                    focused: $inputFocused,
                    onSubmit: submit
                )
            } else {
                WaitingCursor(isWorking: session.isWorking)
                    .contentShape(Rectangle())
                    .onTapGesture { tapped() }
            }
        }
        .background(Theme.background)
        .animation(.easeOut(duration: 0.2), value: session.status)
        .onChange(of: session.mode) {
            // The keyboard follows what the game is asking for: up for a
            // command, away while the room is talking.
            inputFocused = session.mode == .input
        }
        .preferredColorScheme(.dark)
    }

    private func tapped() {
        if session.mode == .input {
            inputFocused = true
        } else {
            Task { await session.acknowledge() }
        }
    }

    private func submit() {
        let text = draft
        draft = ""
        Task { await session.submit(text) }
    }
}
