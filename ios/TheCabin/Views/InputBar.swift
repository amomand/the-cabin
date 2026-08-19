import SwiftUI

/// The command line.
///
/// Deliberately a plain `TextField`: the system keyboard brings the dictation
/// microphone with it, which is most of what dictation needs to work at the
/// cabin, and a custom input view would throw that away.
///
/// One line only. The turn core refuses anything over 200 characters with a
/// line of its own, so there is nothing for a growing field to hold, and a
/// vertical field put the caret a line below the prompt and left a slab of
/// dead space under it.
struct InputBar: View {
    /// The server sends the prompt prefix; the client does not invent one.
    let prompt: String
    let isWorking: Bool
    @Binding var draft: String
    @FocusState.Binding var focused: Bool
    let onSubmit: () -> Void

    var body: some View {
        HStack(alignment: .center, spacing: 0) {
            Text(prompt)
                .foregroundStyle(Theme.echo)
                // The glyph is the field's decoration, not a second control;
                // VoiceOver gets the field alone, named for what it takes.
                .accessibilityHidden(true)
            TextField("", text: $draft)
                .textInputAutocapitalization(.never)
                .autocorrectionDisabled()
                .submitLabel(.go)
                .focused($focused)
                .accessibilityLabel("Command")
                .disabled(isWorking)
                .foregroundStyle(Theme.narration)
                .tint(Theme.narration)
                // Nothing is capped here. The turn core refuses anything over
                // 200 characters with a line of its own, and eating the
                // player's typing would swallow that line and answer with
                // nothing at all.
                .onSubmit(onSubmit)
        }
        .font(Theme.font)
        .padding(.horizontal, Theme.inset)
        .padding(.vertical, 12)
        .frame(maxWidth: .infinity, alignment: .leading)
        .contentShape(Rectangle())
        // The whole row summons the keyboard, not just the field. With the
        // keyboard down this row is a lone prompt, and a lone prompt should
        // be a large target. Not while a turn is in flight, though: focus
        // armed then would raise the keyboard the moment the reply lands.
        .onTapGesture {
            if !isWorking { focused = true }
        }
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
        .padding(.horizontal, Theme.inset)
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
