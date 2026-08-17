import SwiftUI

@main
struct TheCabinApp: App {
    @StateObject private var session = GameSession(
        transport: LocalEngineTransport()
    )
    @Environment(\.scenePhase) private var scenePhase

    var body: some Scene {
        WindowGroup {
            GameView(session: session)
                .task {
                    // Disk first, so the run is intact beneath its launch
                    // opener before anything is asked of the network.
                    session.restore()
                    await session.start()
                }
        }
        .onChange(of: scenePhase) { _, phase in
            Task {
                if phase == .active {
                    await session.resumeFromBackground()
                } else {
                    await session.prepareForBackground()
                }
            }
        }
    }
}
