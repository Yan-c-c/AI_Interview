import Combine
import Foundation

@MainActor
final class HistoryStore: ObservableObject {
    @Published private(set) var records: [HistoryRecord] = []

    private let storageKey = "aiInterviewLite.historyRecords"

    init() {
        load()
    }

    func add(payload: AssistantChatPayload, userMessage: String) {
        let title = makeTitle(intent: payload.intent, userMessage: userMessage)
        let record = HistoryRecord(
            id: UUID(),
            createdAt: Date(),
            title: title,
            intent: payload.intent,
            agent: payload.agent,
            userMessage: userMessage,
            assistantMessage: payload.message ?? "",
            resultText: payload.displayText,
            rawJSON: payload.rawJSON
        )
        records.insert(record, at: 0)
        save()
    }

    func delete(at offsets: IndexSet) {
        for index in offsets.sorted(by: >) {
            records.remove(at: index)
        }
        save()
    }

    func clear() {
        records.removeAll()
        save()
    }

    private func load() {
        guard let data = UserDefaults.standard.data(forKey: storageKey),
              let decoded = try? JSONDecoder().decode([HistoryRecord].self, from: data)
        else { return }
        records = decoded.sorted { $0.createdAt > $1.createdAt }
    }

    private func save() {
        if let data = try? JSONEncoder().encode(records) {
            UserDefaults.standard.set(data, forKey: storageKey)
        }
    }

    private func makeTitle(intent: String, userMessage: String) -> String {
        let firstLine = userMessage
            .split(separator: "\n", omittingEmptySubsequences: true)
            .first
            .map(String.init)?
            .trimmingCharacters(in: .whitespacesAndNewlines)
        if let firstLine, firstLine.count > 6 {
            return firstLine.prefixString(28)
        }
        switch intent {
        case "resume_evaluation": return "简历评估报告"
        case "interview_question_generation": return "模拟面试题"
        case "interview_audio_analysis": return "面试对话分析"
        case "cover_letter_generation": return "求职信生成"
        case "career_planning": return "职业规划"
        case "salary_negotiation": return "谈薪策略"
        case "general_chat": return "智能助手对话"
        default: return "智能助手记录"
        }
    }
}
