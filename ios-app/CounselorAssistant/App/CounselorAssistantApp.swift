import SwiftUI

@main
struct CounselorAssistantApp: App {
    @StateObject private var session = SessionStore()

    var body: some Scene {
        WindowGroup {
            ProductFoundationView()
                .environmentObject(session)
        }
    }
}
