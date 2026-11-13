import Foundation
import SwiftUI

@MainActor
final class AppSettings: ObservableObject {
    static let defaultBackendBaseURL = "http://127.0.0.1:8000"

    @AppStorage("autoSaveHistory") var autoSaveHistory = true

    var backendBaseURL: String {
        Self.defaultBackendBaseURL
    }

    var baseURL: URL? {
        URL(string: Self.defaultBackendBaseURL)
    }
}

@MainActor
final class AppRouter: ObservableObject {
    @Published var selectedTab: AppTab = .home
    @Published var pendingPrompt: String?

    func openShortcut(_ intent: AgentIntent) {
        pendingPrompt = intent.promptTemplate
        selectedTab = .assistant
    }
}

enum AppTab: Hashable {
    case home
    case assistant
    case history
    case profile
}
