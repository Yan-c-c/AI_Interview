import Foundation

enum ReportRenderer {
    static func prettyJSON(from object: Any) -> String {
        guard JSONSerialization.isValidJSONObject(object),
              let data = try? JSONSerialization.data(withJSONObject: object, options: [.prettyPrinted, .sortedKeys]),
              let text = String(data: data, encoding: .utf8)
        else {
            return String(describing: object)
        }
        return text
    }

    static func render(message: String?, result: Any?, fallbackJSON: String) -> String {
        var sections: [String] = []
        if let message, !message.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            sections.append(message)
        }
        guard let dict = result as? [String: Any] else {
            return sections.isEmpty ? fallbackJSON : sections.joined(separator: "\n\n")
        }

        appendDictionarySection("摘要", value: dict["summary"], to: &sections)
        appendDictionarySection("画像", value: dict["resume_profile"] ?? dict["career_profile"] ?? dict["profile"], to: &sections)
        appendDictionarySection("匹配分析", value: dict["matching_analysis"], to: &sections)
        appendDictionarySection("预测", value: dict["prediction"], to: &sections)
        appendDictionarySection("谈薪策略", value: dict["strategy"], to: &sections)
        appendVersions(dict["versions"], to: &sections)
        appendEmail(dict["email"], to: &sections)
        appendQuestionSets(dict["question_sets"], to: &sections)
        appendArraySection("问题清单", value: dict["questions"], to: &sections)
        appendArraySection("逐题分析", value: dict["qa_analysis"], to: &sections)
        appendPlanSections(dict, to: &sections)

        if sections.count <= (message?.isEmpty == false ? 1 : 0) {
            sections.append("```json\n\(fallbackJSON)\n```")
        }
        return sections.joined(separator: "\n\n")
    }

    private static func appendDictionarySection(_ title: String, value: Any?, to sections: inout [String]) {
        guard let dict = value as? [String: Any], !dict.isEmpty else { return }
        let body = dict.map { key, value in "- \(humanize(key)): \(inline(value))" }
            .sorted()
            .joined(separator: "\n")
        if !body.isEmpty {
            sections.append("## \(title)\n\(body)")
        }
    }

    private static func appendArraySection(_ title: String, value: Any?, to sections: inout [String]) {
        guard let items = value as? [Any], !items.isEmpty else { return }
        let body = items.prefix(30).enumerated().map { index, item in
            if let dict = item as? [String: Any] {
                return renderDictionaryItem(index: index + 1, dict: dict)
            }
            return "\(index + 1). \(inline(item))"
        }.joined(separator: "\n\n")
        if !body.isEmpty {
            sections.append("## \(title)\n\(body)")
        }
    }

    private static func appendQuestionSets(_ value: Any?, to sections: inout [String]) {
        guard let sets = value as? [String: Any], !sets.isEmpty else { return }
        var chunks: [String] = []
        for key in sets.keys.sorted() {
            guard let items = sets[key] as? [Any], !items.isEmpty else { continue }
            let rendered = items.prefix(12).enumerated().map { index, item in
                if let dict = item as? [String: Any] {
                    return renderDictionaryItem(index: index + 1, dict: dict)
                }
                return "\(index + 1). \(inline(item))"
            }.joined(separator: "\n\n")
            chunks.append("### \(humanize(key))\n\(rendered)")
        }
        if !chunks.isEmpty {
            sections.append("## 面试题\n" + chunks.joined(separator: "\n\n"))
        }
    }

    private static func appendVersions(_ value: Any?, to sections: inout [String]) {
        guard let versions = value as? [String: Any], !versions.isEmpty else { return }
        let body = versions.keys.sorted().compactMap { key -> String? in
            guard let version = versions[key] as? [String: Any] else { return nil }
            let title = inline(version["title"] ?? humanize(key))
            let content = inline(version["body"] ?? "")
            guard !content.isEmpty else { return nil }
            return "### \(title)\n\(content)"
        }.joined(separator: "\n\n")
        if !body.isEmpty {
            sections.append("## 求职信版本\n\(body)")
        }
    }

    private static func appendEmail(_ value: Any?, to sections: inout [String]) {
        guard let email = value as? [String: Any], !email.isEmpty else { return }
        let subject = inline(email["subject"] ?? "")
        let body = inline(email["body"] ?? "")
        guard !subject.isEmpty || !body.isEmpty else { return }
        sections.append("## 邮件正文\n**主题：** \(subject)\n\n\(body)")
    }

    private static func appendPlanSections(_ dict: [String: Any], to sections: inout [String]) {
        let keys = [
            ("practice_plan", "练习计划"),
            ("career_plan", "职业计划"),
            ("learning_path", "学习路径"),
            ("project_suggestions", "项目补强"),
            ("job_search_strategy", "投递策略"),
            ("next_actions", "下一步"),
            ("optimization_suggestions", "优化建议"),
            ("highlight_points", "亮点提炼"),
            ("main_suggestions", "主要建议")
        ]
        for (key, title) in keys {
            let value = dict[key]
            if value is [String: Any] {
                appendDictionarySection(title, value: value, to: &sections)
            } else {
                appendArraySection(title, value: value, to: &sections)
            }
        }
    }

    private static func renderDictionaryItem(index: Int, dict: [String: Any]) -> String {
        let title = inline(dict["question"] ?? dict["title"] ?? dict["name"] ?? dict["question_id"] ?? "条目 \(index)")
        var lines = ["\(index). \(title)"]
        let preferredKeys = [
            "difficulty", "category", "why_ask", "answer_points", "follow_ups",
            "candidate_answer", "standard_answer", "accuracy_score", "feedback",
            "improvement_suggestion", "related_resume_evidence", "source_type"
        ]
        for key in preferredKeys {
            guard let value = dict[key] else { continue }
            let text = inline(value)
            if !text.isEmpty {
                lines.append("   - \(humanize(key)): \(text)")
            }
        }
        return lines.joined(separator: "\n")
    }

    private static func inline(_ value: Any?) -> String {
        guard let value else { return "" }
        if let string = value as? String { return string.trimmingCharacters(in: .whitespacesAndNewlines) }
        if let bool = value as? Bool { return bool ? "是" : "否" }
        if let number = value as? NSNumber { return number.stringValue }
        if let array = value as? [Any] {
            return array.map { inline($0) }.filter { !$0.isEmpty }.joined(separator: "；")
        }
        if let dict = value as? [String: Any] {
            return dict.map { "\(humanize($0.key))：\(inline($0.value))" }
                .sorted()
                .joined(separator: "；")
        }
        return String(describing: value)
    }

    private static func humanize(_ key: String) -> String {
        let map: [String: String] = [
            "overall_score": "综合评分",
            "risk_level": "风险等级",
            "target_position": "目标岗位",
            "question_count": "题目数量",
            "source_note": "来源说明",
            "target_salary": "目标薪资",
            "reasonable_range": "合理区间",
            "minimum_acceptable_salary": "最低可接受",
            "offer_decision": "Offer 判断",
            "current_stage": "当前阶段",
            "target_direction": "目标方向",
            "match_score": "匹配分",
            "matched_skills": "已匹配技能",
            "missing_skills": "缺口技能",
            "risk_points": "风险点"
        ]
        return map[key] ?? key.replacingOccurrences(of: "_", with: " ")
    }
}
