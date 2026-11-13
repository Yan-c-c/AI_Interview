import SwiftUI

enum AuthMode {
    case login
    case register
}

struct AuthView: View {
    @EnvironmentObject private var settings: AppSettings
    @EnvironmentObject private var authStore: AuthStore

    @State private var mode: AuthMode = .login
    @State private var name = ""
    @State private var email = ""
    @State private var password = ""

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 20) {
                    ZStack(alignment: .leading) {
                        TechSignalPanel(compact: true)
                        VStack(alignment: .leading, spacing: 10) {
                            Image(systemName: "sparkles.rectangle.stack")
                                .font(.system(size: 28, weight: .semibold))
                                .foregroundStyle(.white)
                            Text("智能面试助手")
                                .font(.largeTitle.bold())
                                .foregroundStyle(.white)
                            Text(mode == .login ? "登录账号" : "注册账号")
                                .font(.headline.weight(.medium))
                                .foregroundStyle(.white.opacity(0.78))
                        }
                        .padding(20)
                    }

                    VStack(spacing: 14) {
                        if mode == .register {
                            TextField("姓名", text: $name)
                                .textContentType(.name)
                                .textInputAutocapitalization(.never)
                                .formTextField()
                        }

                        TextField("邮箱", text: $email)
                            .keyboardType(.emailAddress)
                            .textContentType(.emailAddress)
                            .textInputAutocapitalization(.never)
                            .formTextField()

                        SecureField("密码", text: $password)
                            .textContentType(mode == .login ? .password : .newPassword)
                            .formTextField()
                    }
                    .padding(16)
                    .background(.background, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
                    .overlay(
                        RoundedRectangle(cornerRadius: 8, style: .continuous)
                            .stroke(Color(.separator).opacity(0.18), lineWidth: 1)
                    )

                    if let error = authStore.authError {
                        Label(error, systemImage: "exclamationmark.triangle")
                            .font(.footnote)
                            .foregroundStyle(.red)
                    }

                    Button {
                        Task { await submit() }
                    } label: {
                        HStack {
                            if authStore.isCheckingSession {
                                ProgressView().tint(.white)
                            } else {
                                Image(systemName: mode == .login ? "arrow.right.circle.fill" : "person.badge.plus")
                            }
                            Text(mode == .login ? "登录" : "注册")
                        }
                        .frame(maxWidth: .infinity)
                    }
                    .buttonStyle(.borderedProminent)
                    .controlSize(.large)
                    .disabled(authStore.isCheckingSession || !canSubmit)

                    Button {
                        withAnimation(.easeOut(duration: 0.2)) {
                            mode = mode == .login ? .register : .login
                            authStore.authError = nil
                        }
                    } label: {
                        Text(mode == .login ? "没有账号，去注册" : "已有账号，去登录")
                            .frame(maxWidth: .infinity)
                    }
                    .buttonStyle(.plain)
                    .foregroundStyle(.blue)
                }
                .padding(20)
            }
            .background(Color(.systemGroupedBackground))
            .scrollDismissesKeyboard(.interactively)
        }
    }

    private var canSubmit: Bool {
        let hasAccount = email.contains("@") && password.count >= 6
        if mode == .register {
            return hasAccount && !name.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
        }
        return hasAccount
    }

    private func submit() async {
        switch mode {
        case .login:
            await authStore.login(baseURL: settings.baseURL, email: email, password: password)
        case .register:
            await authStore.register(baseURL: settings.baseURL, name: name, email: email, password: password)
        }
    }
}

extension View {
    func formTextField() -> some View {
        self
            .font(.body)
            .padding(.horizontal, 14)
            .padding(.vertical, 12)
            .background(Color(.secondarySystemGroupedBackground), in: RoundedRectangle(cornerRadius: 8, style: .continuous))
            .overlay(
                RoundedRectangle(cornerRadius: 8, style: .continuous)
                    .stroke(Color(.separator).opacity(0.4), lineWidth: 0.5)
            )
    }
}
