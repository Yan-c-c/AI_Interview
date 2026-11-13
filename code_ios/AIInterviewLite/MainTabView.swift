import SwiftUI

struct MainTabView: View {
    @EnvironmentObject private var router: AppRouter

    var body: some View {
        TabView(selection: $router.selectedTab) {
            HomeView()
                .tabItem {
                    Label("首页", systemImage: "house")
                }
                .tag(AppTab.home)

            AssistantView()
                .tabItem {
                    Label("助手", systemImage: "message")
                }
                .tag(AppTab.assistant)

            HistoryView()
                .tabItem {
                    Label("历史", systemImage: "clock")
                }
                .tag(AppTab.history)

            ProfileView()
                .tabItem {
                    Label("我的", systemImage: "person.crop.circle")
                }
                .tag(AppTab.profile)
        }
    }
}
