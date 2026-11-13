import Combine
import Foundation

@MainActor
final class AuthStore: ObservableObject {
    @Published private(set) var user: AuthUser?
    @Published private(set) var isCheckingSession = false
    @Published var authError: String?

    private let userDefaultsKey = "aiInterviewLite.currentUser"

    var token: String? {
        KeychainService.loadToken()
    }

    var isAuthenticated: Bool {
        user != nil && token != nil
    }

    init() {
        loadCachedUser()
    }

    func validateSavedSession(baseURL: URL?) async {
        guard let baseURL, let token else {
            logout()
            return
        }
        isCheckingSession = true
        defer { isCheckingSession = false }
        do {
            let freshUser = try await APIClient.fetchMe(baseURL: baseURL, token: token)
            cache(user: freshUser)
            authError = nil
        } catch {
            logout()
            authError = "登录已过期，请重新登录。"
        }
    }

    func login(baseURL: URL?, email: String, password: String) async {
        guard let baseURL else {
            authError = "默认后端地址无效。"
            return
        }
        isCheckingSession = true
        defer { isCheckingSession = false }
        do {
            let response = try await APIClient.login(baseURL: baseURL, email: email, password: password)
            try KeychainService.saveToken(response.token)
            cache(user: response.user)
            authError = nil
        } catch {
            authError = error.localizedDescription
        }
    }

    func register(baseURL: URL?, name: String, email: String, password: String) async {
        guard let baseURL else {
            authError = "默认后端地址无效。"
            return
        }
        isCheckingSession = true
        defer { isCheckingSession = false }
        do {
            let response = try await APIClient.register(baseURL: baseURL, name: name, email: email, password: password)
            try KeychainService.saveToken(response.token)
            cache(user: response.user)
            authError = nil
        } catch {
            authError = error.localizedDescription
        }
    }

    func logout() {
        KeychainService.deleteToken()
        user = nil
        UserDefaults.standard.removeObject(forKey: userDefaultsKey)
    }

    private func cache(user: AuthUser) {
        self.user = user
        if let data = try? JSONEncoder().encode(user) {
            UserDefaults.standard.set(data, forKey: userDefaultsKey)
        }
    }

    private func loadCachedUser() {
        guard let data = UserDefaults.standard.data(forKey: userDefaultsKey),
              let cached = try? JSONDecoder().decode(AuthUser.self, from: data)
        else { return }
        user = cached
    }
}
