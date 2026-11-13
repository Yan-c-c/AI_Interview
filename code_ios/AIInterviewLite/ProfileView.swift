import SwiftUI

struct ProfileView: View {
    @EnvironmentObject private var settings: AppSettings
    @EnvironmentObject private var authStore: AuthStore
    @EnvironmentObject private var historyStore: HistoryStore

    @State private var statusMessage = ""
    @State private var showLogoutConfirm = false
    @State private var showClearConfirm = false

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 16) {
                    ProfileAccountCard(user: authStore.user)

                    HStack(spacing: 12) {
                        ProfileMetricTile(title: "历史记录", value: "\(historyStore.records.count)", caption: "本地保存")
                        ProfileMetricTile(title: "Token", value: authStore.token == nil ? "未保存" : "已保存", caption: "Keychain")
                    }

                    VStack(spacing: 0) {
                        settingsRow(title: "自动保存历史", systemImage: "clock.arrow.circlepath") {
                            Toggle("", isOn: $settings.autoSaveHistory)
                                .labelsHidden()
                        }
                        Divider().padding(.leading, 42)
                        settingsRow(title: "账号状态", systemImage: "checkmark.seal") {
                            Text(authStore.user?.status.rawValue ?? "unknown")
                                .foregroundStyle(.secondary)
                        }
                        Divider().padding(.leading, 42)
                        settingsRow(title: "角色", systemImage: "person.text.rectangle") {
                            Text(authStore.user?.role.rawValue ?? "user")
                                .foregroundStyle(.secondary)
                        }
                    }
                    .profileCard()

                    VStack(spacing: 12) {
                        Button {
                            Task { await validateToken() }
                        } label: {
                            Label(authStore.isCheckingSession ? "校验中" : "校验登录", systemImage: "checkmark.shield")
                                .frame(maxWidth: .infinity)
                        }
                        .buttonStyle(.bordered)
                        .controlSize(.large)
                        .disabled(authStore.isCheckingSession)

                        if !statusMessage.isEmpty {
                            Text(statusMessage)
                                .font(.footnote)
                                .foregroundStyle(.secondary)
                                .frame(maxWidth: .infinity, alignment: .leading)
                        }

                        Button(role: .destructive) {
                            showClearConfirm = true
                        } label: {
                            Label("清空历史", systemImage: "trash")
                                .frame(maxWidth: .infinity)
                        }
                        .buttonStyle(.bordered)
                        .controlSize(.large)
                        .disabled(historyStore.records.isEmpty)

                        Button(role: .destructive) {
                            showLogoutConfirm = true
                        } label: {
                            Label("退出登录", systemImage: "rectangle.portrait.and.arrow.right")
                                .frame(maxWidth: .infinity)
                        }
                        .buttonStyle(.borderedProminent)
                        .controlSize(.large)
                        .tint(.red)
                    }
                    .padding(14)
                    .profileCard()
                }
                .padding(16)
            }
            .background(Color(.systemGroupedBackground))
            .navigationTitle("我的")
            .navigationBarTitleDisplayMode(.inline)
            .confirmationDialog("退出登录", isPresented: $showLogoutConfirm, titleVisibility: .visible) {
                Button("退出", role: .destructive) {
                    authStore.logout()
                }
            }
            .confirmationDialog("清空历史", isPresented: $showClearConfirm, titleVisibility: .visible) {
                Button("清空", role: .destructive) {
                    historyStore.clear()
                }
            }
        }
    }

    private func settingsRow<Accessory: View>(
        title: String,
        systemImage: String,
        @ViewBuilder accessory: () -> Accessory
    ) -> some View {
        HStack(spacing: 12) {
            Image(systemName: systemImage)
                .font(.system(size: 16, weight: .semibold))
                .foregroundStyle(.blue)
                .frame(width: 30, height: 30)
                .background(Color.blue.opacity(0.1), in: RoundedRectangle(cornerRadius: 8, style: .continuous))
            Text(title)
                .font(.body)
            Spacer()
            accessory()
        }
        .padding(14)
    }

    private func validateToken() async {
        await authStore.validateSavedSession(baseURL: settings.baseURL)
        statusMessage = authStore.isAuthenticated ? "登录有效" : "登录无效"
    }
}

struct ProfileAccountCard: View {
    let user: AuthUser?

    var body: some View {
        ZStack(alignment: .bottomLeading) {
            TechSignalPanel(compact: true)
            HStack(spacing: 14) {
                Text(user.flatMap { $0.name.first.map(String.init) } ?? "U")
                    .font(.title2.bold())
                    .foregroundStyle(.white)
                    .frame(width: 58, height: 58)
                    .background(Color.white.opacity(0.16), in: RoundedRectangle(cornerRadius: 8, style: .continuous))
                    .overlay(
                        RoundedRectangle(cornerRadius: 8, style: .continuous)
                            .stroke(Color.white.opacity(0.18), lineWidth: 1)
                    )

                VStack(alignment: .leading, spacing: 6) {
                    Text(user?.name ?? "用户")
                        .font(.title3.bold())
                        .foregroundStyle(.white)
                    Text(user?.email ?? "")
                        .font(.subheadline)
                        .foregroundStyle(.white.opacity(0.78))
                        .lineLimit(1)
                        .minimumScaleFactor(0.78)
                    Text("智能面试助手账号")
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(.white.opacity(0.72))
                }
                Spacer(minLength: 0)
            }
            .padding(18)
        }
    }
}

struct ProfileMetricTile: View {
    let title: String
    let value: String
    let caption: String

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(title)
                .font(.caption)
                .foregroundStyle(.secondary)
            Text(value)
                .font(value.count > 4 ? .headline.bold() : .title2.bold())
                .lineLimit(1)
                .minimumScaleFactor(0.72)
            Text(caption)
                .font(.caption2)
                .foregroundStyle(.secondary)
                .lineLimit(1)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(14)
        .profileCard()
    }
}

extension View {
    func profileCard() -> some View {
        self
            .background(.background, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
            .overlay(
                RoundedRectangle(cornerRadius: 8, style: .continuous)
                    .stroke(Color(.separator).opacity(0.18), lineWidth: 1)
            )
    }
}
