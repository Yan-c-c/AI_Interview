import SwiftUI

struct AssistantView: View {
    @EnvironmentObject private var settings: AppSettings
    @EnvironmentObject private var authStore: AuthStore
    @EnvironmentObject private var historyStore: HistoryStore
    @EnvironmentObject private var router: AppRouter

    @State private var messages: [ChatMessage] = [
        ChatMessage(role: .assistant, text: "把简历、项目、岗位、面试回答或 Offer 信息贴进来，我会调用后端 Agent 处理。")
    ]
    @State private var draft = ""
    @State private var sessionID = UUID().uuidString
    @State private var isSending = false

    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                shortcutStrip
                Divider()
                messageList
                Divider()
                composer
            }
            .navigationTitle("助手")
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button {
                        messages = []
                        sessionID = UUID().uuidString
                    } label: {
                        Image(systemName: "trash")
                    }
                    .disabled(messages.isEmpty || isSending)
                }
            }
            .onAppear {
                consumePendingPrompt()
            }
            .onChange(of: router.pendingPrompt) { _ in
                consumePendingPrompt()
            }
        }
    }

    private var shortcutStrip: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 8) {
                ForEach(AgentIntent.allCases) { intent in
                    Button {
                        draft = intent.promptTemplate
                    } label: {
                        Label(intent.title, systemImage: intent.symbolName)
                            .labelStyle(.titleAndIcon)
                            .font(.footnote.weight(.medium))
                    }
                    .buttonStyle(.bordered)
                    .tint(Color.intentTint(intent.tintName))
                }
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 10)
        }
        .background(Color(.systemBackground))
    }

    private var messageList: some View {
        ScrollViewReader { proxy in
            ScrollView {
                LazyVStack(spacing: 14) {
                    ForEach(messages) { message in
                        ChatBubble(message: message)
                            .id(message.id)
                    }
                    if isSending {
                        HStack {
                            ProgressView()
                            Text("生成中")
                                .font(.footnote)
                                .foregroundStyle(.secondary)
                            Spacer()
                        }
                        .padding(.horizontal, 16)
                    }
                }
                .padding(.vertical, 16)
            }
            .background(Color(.systemGroupedBackground))
            .onChange(of: messages.count) { _ in
                if let last = messages.last {
                    withAnimation(.easeOut(duration: 0.2)) {
                        proxy.scrollTo(last.id, anchor: .bottom)
                    }
                }
            }
        }
    }

    private var composer: some View {
        VStack(spacing: 10) {
            TextEditor(text: $draft)
                .font(.body)
                .frame(minHeight: 96, maxHeight: 150)
                .padding(10)
                .scrollContentBackground(.hidden)
                .background(Color(.secondarySystemGroupedBackground), in: RoundedRectangle(cornerRadius: 8, style: .continuous))
                .overlay(
                    RoundedRectangle(cornerRadius: 8, style: .continuous)
                        .stroke(Color(.separator).opacity(0.45), lineWidth: 0.5)
                )

            HStack {
                Text("\(draft.count) 字")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                Spacer()
                Button {
                    Task { await send() }
                } label: {
                    Label("发送", systemImage: "paperplane.fill")
                }
                .buttonStyle(.borderedProminent)
                .disabled(isSending || draft.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
            }
        }
        .padding(12)
        .background(.background)
    }

    private func consumePendingPrompt() {
        guard let prompt = router.pendingPrompt else { return }
        draft = prompt
        router.pendingPrompt = nil
    }

    private func send() async {
        let text = draft.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty, let baseURL = settings.baseURL else { return }
        draft = ""
        isSending = true
        messages.append(ChatMessage(role: .user, text: text))
        do {
            let payload = try await APIClient.chat(
                baseURL: baseURL,
                token: authStore.token,
                message: text,
                sessionID: sessionID
            )
            let reply = payload.displayText.isEmpty ? (payload.message ?? "已完成。") : payload.displayText
            messages.append(ChatMessage(role: .assistant, text: reply))
            if settings.autoSaveHistory {
                historyStore.add(payload: payload, userMessage: text)
            }
        } catch {
            messages.append(ChatMessage(role: .assistant, text: "请求失败：\(error.localizedDescription)"))
        }
        isSending = false
    }
}

struct ChatBubble: View {
    let message: ChatMessage

    private var isUser: Bool {
        message.role == .user
    }

    var body: some View {
        HStack(alignment: .top) {
            if isUser { Spacer(minLength: 36) }
            VStack(alignment: .leading, spacing: 6) {
                MarkdownText(message.text)
                    .font(.body)
                    .foregroundStyle(isUser ? .white : .primary)
                    .textSelection(.enabled)
                Text(message.createdAt, style: .time)
                    .font(.caption2)
                    .foregroundStyle(isUser ? .white.opacity(0.75) : .secondary)
            }
            .padding(12)
            .background(
                isUser ? Color.blue : Color(.secondarySystemGroupedBackground),
                in: RoundedRectangle(cornerRadius: 14, style: .continuous)
            )
            if !isUser { Spacer(minLength: 36) }
        }
        .padding(.horizontal, 16)
    }
}

struct MarkdownText: View {
    private let text: String

    init(_ text: String) {
        self.text = text
    }

    var body: some View {
        if let attributed = try? AttributedString(markdown: text) {
            Text(attributed)
        } else {
            Text(text)
        }
    }
}
