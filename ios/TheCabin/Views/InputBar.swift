import SwiftUI

/// The command line.
///
/// Deliberately a plain `TextField`: the system keyboard brings the dictation
/// microphone with it, which is most of what dictation needs to work at the
/// cabin, and a custom input view would throw that away.
struct InputBar: View {
    /// The server sends the prompt prefix; the client does not invent one.
    let prompt: String
    let isWorking: Bool
    @Binding var draft: String
    @FocusState.Binding var focused: Bool
    let onSubmit: () -> Void

    var body: some View {
        HStack(alignment: .firstTextBaseline, spacing: 0) {
            Text(prompt)
                .foregroundStyle(Theme.echo)
            TextField("", text: $draft, axis: .vertical)
                .textInputAutocapitalization(.never)
                .autocorrectionDisabled()
                .submitLabel(.go)
                .focused($focused)
                .accessibilityLabel(Text(prompt))
                .disabled(isWorking)
                .foregroundStyle(Theme.narration)
                .tint(Theme.narration)
                .lineLimit(1...4)
                .onChange(of: draft) {
                    // Nothing is capped here. The turn core refuses anything
                    // over 200 characters with a line of its own, and eating
                    // the player's typing would swallow that line and answer
                    // with nothing at all.
                    //
                    // A vertical field takes newlines instead of submitting, so
                    // the return key is caught here.
                    if draft.contains("\n") {
                        draft = draft.replacingOccurrences(of: "\n", with: "")
                        onSubmit()
                    }
                }
        }
        .font(Theme.font)
        .padding(.horizontal, 16)
        .padding(.vertical, 12)
        .background(Theme.background)
        .overlay(alignment: .top) {
            Rectangle()
                .fill(Theme.rule)
                .frame(height: 1)
        }
        .opacity(isWorking ? 0.4 : 1)
        .animation(.easeOut(duration: 0.15), value: isWorking)
    }
}

/// What stands in for the input bar when the game wants a key, or has ended.
///
/// A cursor rather than an instruction: nothing here needs words, and words
/// here would be the client talking.
struct WaitingCursor: View {
    let isWorking: Bool
    @State private var dim = false

    var body: some View {
        HStack {
            Text("\u{2588}")
                .font(Theme.font)
                .foregroundStyle(Theme.echo)
                .opacity(dim ? 0.15 : 0.9)
            Spacer()
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 12)
        .frame(maxWidth: .infinity, alignment: .leading)
        .contentShape(Rectangle())
        .onAppear { start() }
        .onChange(of: isWorking) { start() }
    }

    private func start() {
        dim = false
        // Faster while a turn is in flight, so the wait reads as the room
        // thinking rather than the app hanging.
        withAnimation(.easeInOut(duration: isWorking ? 0.4 : 0.9).repeatForever(autoreverses: true)) {
            dim = true
        }
    }
}
