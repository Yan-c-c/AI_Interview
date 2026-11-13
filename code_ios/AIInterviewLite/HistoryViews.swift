import SwiftUI

struct HistoryView: View {
    @EnvironmentObject private var historyStore: HistoryStore
    @State private var searchText = ""
    @State private var showClearConfirm = false

    private var filteredRecords: [HistoryRecord] {
        let query = searchText.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !query.isEmpty else { return historyStore.records }
        return historyStore.records.filter {
            $0.title.localizedCaseInsensitiveContains(query)
            || $0.userMessage.localizedCaseInsensitiveContains(query)
            || $0.resultText.localizedCaseInsensitiveContains(query)
        }
    }

    var body: some View {
        NavigationStack {
            Group {
                if filteredRecords.isEmpty {
                    EmptyStateView(
                        symbolName: "clock.badge.questionmark",
                        title: searchText.isEmpty ? "暂无历史" : "未找到记录",
                        subtitle: searchText.isEmpty ? "生成过的报告和对话会保存在这里。" : "换个关键词再试。"
                    )
                } else {
                    List {
                        ForEach(filteredRecords) { record in
                            NavigationLink {
                                HistoryDetailView(record: record)
                            } label: {
                                HistoryRow(record: record)
                            }
                        }
                        .onDelete(perform: delete)
                    }
                    .listStyle(.plain)
                }
            }
            .navigationTitle("历史")
            .searchable(text: $searchText, prompt: "搜索历史")
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button {
                        showClearConfirm = true
                    } label: {
                        Image(systemName: "trash")
                    }
                    .disabled(historyStore.records.isEmpty)
                }
            }
            .confirmationDialog("清空历史", isPresented: $showClearConfirm, titleVisibility: .visible) {
                Button("清空", role: .destructive) {
                    historyStore.clear()
                }
            }
        }
    }

    private func delete(at offsets: IndexSet) {
        if searchText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            historyStore.delete(at: offsets)
            return
        }
        let ids = offsets.map { filteredRecords[$0].id }
        let originalOffsets = IndexSet(historyStore.records.indices.filter { ids.contains(historyStore.records[$0].id) })
        historyStore.delete(at: originalOffsets)
    }
}

struct HistoryRow: View {
    let record: HistoryRecord

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack {
                Text(record.title)
                    .font(.headline)
                    .lineLimit(1)
                Spacer()
                Text(record.createdAt, style: .date)
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            Text(record.preview)
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .lineLimit(2)
            HStack(spacing: 6) {
                Text(intentLabel(record.intent))
                    .font(.caption2.weight(.medium))
                    .padding(.horizontal, 8)
                    .padding(.vertical, 4)
                    .background(Color.blue.opacity(0.12), in: Capsule())
                    .foregroundStyle(.blue)
                if let agent = record.agent {
                    Text(agent)
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                        .lineLimit(1)
                }
            }
        }
        .padding(.vertical, 6)
    }

    private func intentLabel(_ intent: String) -> String {
        switch intent {
        case "resume_evaluation": return "简历"
        case "interview_question_generation": return "面试"
        case "interview_audio_analysis": return "对话分析"
        case "cover_letter_generation": return "求职信"
        case "career_planning": return "规划"
        case "salary_negotiation": return "谈薪"
        case "general_chat": return "对话"
        default: return "记录"
        }
    }
}

struct HistoryDetailView: View {
    let record: HistoryRecord
    @State private var showRawJSON = false

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 18) {
                VStack(alignment: .leading, spacing: 8) {
                    Text(record.title)
                        .font(.title2.bold())
                    Text(record.createdAt.formatted(date: .abbreviated, time: .shortened))
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                }

                DetailSection(title: "输入") {
                    Text(record.userMessage)
                        .textSelection(.enabled)
                }

                DetailSection(title: "结果") {
                    MarkdownText(record.resultText.isEmpty ? record.assistantMessage : record.resultText)
                        .textSelection(.enabled)
                }

                DisclosureGroup("原始 JSON", isExpanded: $showRawJSON) {
                    ScrollView(.horizontal) {
                        Text(record.rawJSON)
                            .font(.system(.footnote, design: .monospaced))
                            .textSelection(.enabled)
                    }
                    .padding(.top, 8)
                }
                .font(.subheadline.weight(.medium))
            }
            .padding(16)
        }
        .background(Color(.systemGroupedBackground))
        .navigationTitle("记录")
        .navigationBarTitleDisplayMode(.inline)
    }
}

struct DetailSection<Content: View>: View {
    let title: String
    @ViewBuilder var content: Content

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text(title)
                .font(.headline)
            content
                .font(.body)
                .frame(maxWidth: .infinity, alignment: .leading)
        }
        .padding(14)
        .background(Color(.secondarySystemGroupedBackground), in: RoundedRectangle(cornerRadius: 8, style: .continuous))
    }
}

struct EmptyStateView: View {
    let symbolName: String
    let title: String
    let subtitle: String

    var body: some View {
        VStack(spacing: 12) {
            Image(systemName: symbolName)
                .font(.system(size: 40, weight: .semibold))
                .foregroundStyle(.secondary)
            Text(title)
                .font(.headline)
            Text(subtitle)
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
        }
        .padding(28)
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(Color(.systemGroupedBackground))
    }
}
