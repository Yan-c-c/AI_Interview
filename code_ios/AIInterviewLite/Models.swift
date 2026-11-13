import Foundation

enum UserRole: String, Codable {
    case user
    case admin
}

enum UserStatus: String, Codable {
    case active
    case disabled
}

struct AuthUser: Codable, Identifiable, Equatable {
    let id: String
    let name: String
    let email: String
    let role: UserRole
    let status: UserStatus
    let createdAt: String?
    let updatedAt: String?
    let lastLoginAt: String?

    enum CodingKeys: String, CodingKey {
        case id
        case name
        case email
        case role
        case status
        case createdAt = "created_at"
        case updatedAt = "updated_at"
        case lastLoginAt = "last_login_at"
    }
}

struct AuthResponse: Decodable {
    let success: Bool
    let user: AuthUser
    let token: String
}

struct MeResponse: Decodable {
    let success: Bool
    let user: AuthUser
}

enum ChatRole: String, Codable {
    case user
    case assistant
    case system
}

struct ChatMessage: Identifiable, Codable, Equatable {
    let id: UUID
    let role: ChatRole
    let text: String
    let createdAt: Date

    init(id: UUID = UUID(), role: ChatRole, text: String, createdAt: Date = Date()) {
        self.id = id
        self.role = role
        self.text = text
        self.createdAt = createdAt
    }
}

struct HistoryRecord: Identifiable, Codable, Equatable {
    let id: UUID
    let createdAt: Date
    var title: String
    var intent: String
    var agent: String?
    var userMessage: String
    var assistantMessage: String
    var resultText: String
    var rawJSON: String

    var preview: String {
        let source = resultText.isEmpty ? assistantMessage : resultText
        return source.replacingOccurrences(of: "\n", with: " ").prefixString(96)
    }
}

struct AssistantChatPayload {
    let success: Bool
    let intent: String
    let agent: String?
    let message: String?
    let result: Any?
    let displayText: String
    let rawJSON: String
}

enum AgentIntent: String, CaseIterable, Identifiable, Codable {
    case resumeEvaluation
    case mockInterview
    case coverLetter
    case careerPlanning
    case salaryNegotiation
    case emailPolish

    var id: String { rawValue }

    var title: String {
        switch self {
        case .resumeEvaluation: return "简历评估"
        case .mockInterview: return "模拟面试"
        case .coverLetter: return "求职信"
        case .careerPlanning: return "职业规划"
        case .salaryNegotiation: return "谈薪助手"
        case .emailPolish: return "邮件润色"
        }
    }

    var subtitle: String {
        switch self {
        case .resumeEvaluation: return "粘贴简历文本，生成优化建议"
        case .mockInterview: return "岗位、技能、项目驱动问答"
        case .coverLetter: return "公司、岗位、JD 生成正文"
        case .careerPlanning: return "背景、目标、困惑形成路径"
        case .salaryNegotiation: return "Offer、城市、经验谈判策略"
        case .emailPolish: return "只生成或润色邮件正文"
        }
    }

    var symbolName: String {
        switch self {
        case .resumeEvaluation: return "doc.text.magnifyingglass"
        case .mockInterview: return "person.2.wave.2"
        case .coverLetter: return "doc.richtext"
        case .careerPlanning: return "point.topleft.down.curvedto.point.bottomright.up"
        case .salaryNegotiation: return "banknote"
        case .emailPolish: return "envelope.badge"
        }
    }

    var tintName: String {
        switch self {
        case .resumeEvaluation: return "blue"
        case .mockInterview: return "teal"
        case .coverLetter: return "indigo"
        case .careerPlanning: return "green"
        case .salaryNegotiation: return "orange"
        case .emailPolish: return "pink"
        }
    }

    var promptTemplate: String {
        switch self {
        case .resumeEvaluation:
            return """
            请帮我评估这份简历，指出岗位匹配度、主要风险、可量化优化建议和改写方向。

            目标岗位：

            简历文本：

            """
        case .mockInterview:
            return """
            请基于以下岗位、技能栈和项目经历生成个性化面试题，并开始文字模拟面试。

            目标岗位：
            技能栈：
            项目经历：
            希望面试难度：

            """
        case .coverLetter:
            return """
            请生成一封个性化求职信，包含正式版和邮件精简版。

            目标公司：
            目标岗位：
            招聘 JD：
            个人背景：
            希望风格：

            """
        case .careerPlanning:
            return """
            请为我生成职业规划，包含能力画像、目标岗位匹配、学习路径、项目补强和投递策略。

            当前背景：
            目标方向：
            当前困惑：
            可投入时间：
            期望城市/行业：

            """
        case .salaryNegotiation:
            return """
            请作为谈薪助手，根据以下信息生成薪资判断、谈判策略和 HR 话术。

            岗位：
            城市：
            工作年限：
            技能栈：
            当前 Offer：
            期望薪资：
            其他约束：

            """
        case .emailPolish:
            return """
            请帮我生成或润色求职邮件正文，只输出邮件主题、正文和可替换版本，不要执行发送。

            目标公司：
            目标岗位：
            收件人：
            原邮件/想表达的内容：
            个人背景：
            希望语气：

            """
        }
    }
}

extension String {
    func prefixString(_ count: Int) -> String {
        if self.count <= count { return self }
        return String(prefix(count)) + "..."
    }
}
