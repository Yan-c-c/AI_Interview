import SwiftUI

@main
struct AIInterviewLiteApp: App {
    @StateObject private var settings = AppSettings()
    @StateObject private var authStore = AuthStore()
    @StateObject private var historyStore = HistoryStore()
    @StateObject private var router = AppRouter()

    var body: some Scene {
        WindowGroup {
            RootView()
                .environmentObject(settings)
                .environmentObject(authStore)
                .environmentObject(historyStore)
                .environmentObject(router)
                .task {
                    await authStore.validateSavedSession(baseURL: settings.baseURL)
                }
        }
    }
}

struct RootView: View {
    @EnvironmentObject private var authStore: AuthStore

    var body: some View {
        Group {
            if authStore.isCheckingSession && !authStore.isAuthenticated {
                LaunchLoadingView()
            } else if authStore.isAuthenticated {
                MainTabView()
            } else {
                AuthView()
            }
        }
    }
}

struct LaunchLoadingView: View {
    var body: some View {
        VStack(spacing: 16) {
            ProgressView()
            Text("正在校验登录状态")
                .font(.subheadline)
                .foregroundStyle(.secondary)
        }
    }
}
