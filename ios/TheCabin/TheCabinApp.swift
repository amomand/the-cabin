import SwiftUI

@main
struct TheCabinApp: App {
    @StateObject private var session = GameSession(
        transport: ServerTransport(clientID: ClientIdentity.current())
    )
    @Environment(\.scenePhase) private var scenePhase

    var body: some Scene {
        WindowGroup {
            GameView(session: session)
                .task {
                    // Disk first, so the run is on screen before anything is
                    // asked of the network.
                    session.restore()
                    await session.start()
                }
        }
        .onChange(of: scenePhase) { _, phase in
            guard phase == .active else { return }
            Task { await session.resumeFromBackground() }
        }
    }
}
