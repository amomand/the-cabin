import SwiftUI

/// The whole screen: status above, transcript in the middle, input below.
struct GameView: View {
    @ObservedObject var session: GameSession
    @State private var draft = ""
    @FocusState private var inputFocused: Bool

    var body: some View {
        VStack(spacing: 0) {
            StatusLineView(
                status: session.launchOpenerLines == nil ? session.status : nil,
                onOpenNotebook: openNotebook
            )
            .transition(.opacity)

            Group {
                if let lines = session.launchOpenerLines {
                    LaunchOpenerView(lines: lines, onDismiss: dismissLaunchOpener)
                } else {
                    VStack(spacing: 0) {
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
                }
            }
        }
        .background(Theme.background)
        .animation(.easeOut(duration: 0.2), value: session.status)
        .onChange(of: session.mode) {
            // The keyboard follows what the game is asking for: up for a
            // command, away while the room is talking.
            inputFocused = session.launchOpenerLines == nil && session.mode == .input
        }
        .onChange(of: session.launchOpenerLines) {
            if session.launchOpenerLines != nil {
                inputFocused = false
            }
        }
        .onChange(of: session.playtestNoteDraft?.id) {
            if session.playtestNoteDraft == nil,
               session.launchOpenerLines == nil,
               session.mode == .input {
                inputFocused = true
            }
        }
        .sheet(isPresented: notebookIsPresented) {
            PlaytestNoteSheet(session: session)
        }
        .preferredColorScheme(.dark)
    }

    private var notebookIsPresented: Binding<Bool> {
        Binding(
            get: { session.playtestNoteDraft != nil },
            set: { if !$0 { session.cancelPlaytestNote() } }
        )
    }

    private func openNotebook() {
        inputFocused = false
        session.beginPlaytestNote()
    }

    private func dismissLaunchOpener() {
        session.dismissLaunchOpener()
        inputFocused = session.mode == .input
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
