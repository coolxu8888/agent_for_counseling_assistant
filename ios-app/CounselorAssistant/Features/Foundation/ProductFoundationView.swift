import SwiftUI

struct ProductFoundationView: View {
    @EnvironmentObject private var session: SessionStore

    var body: some View {
        Group {
            if session.isRestoring {
                ProgressView("正在恢复安全会话")
            } else if session.user == nil {
                LoginView()
            } else {
                CaseListView()
            }
        }
        .task {
            await session.restoreSession()
        }
    }
}

#Preview {
    ProductFoundationView()
        .environmentObject(SessionStore.preview)
}
