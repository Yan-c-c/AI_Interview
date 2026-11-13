import Foundation

enum APIError: LocalizedError {
    case invalidBaseURL
    case invalidResponse
    case server(String)
    case malformedPayload

    var errorDescription: String? {
        switch self {
        case .invalidBaseURL:
            return "后端地址无效"
        case .invalidResponse:
            return "后端响应无效"
        case .server(let message):
            return message
        case .malformedPayload:
            return "后端返回格式无法解析"
        }
    }
}

enum APIClient {
    static func login(baseURL: URL, email: String, password: String) async throws -> AuthResponse {
        let data = try await requestData(
            baseURL: baseURL,
            path: "api/admin/auth/login",
            method: "POST",
            token: nil,
            body: ["email": email, "password": password]
        )
        return try JSONDecoder.api.decode(AuthResponse.self, from: data)
    }

    static func register(baseURL: URL, name: String, email: String, password: String) async throws -> AuthResponse {
        let data = try await requestData(
            baseURL: baseURL,
            path: "api/admin/auth/register",
            method: "POST",
            token: nil,
            body: ["name": name, "email": email, "password": password]
        )
        return try JSONDecoder.api.decode(AuthResponse.self, from: data)
    }

    static func fetchMe(baseURL: URL, token: String) async throws -> AuthUser {
        let data = try await requestData(
            baseURL: baseURL,
            path: "api/admin/auth/me",
            method: "GET",
            token: token,
            body: nil
        )
        return try JSONDecoder.api.decode(MeResponse.self, from: data).user
    }

    static func chat(baseURL: URL, token: String?, message: String, sessionID: String) async throws -> AssistantChatPayload {
        let data = try await requestData(
            baseURL: baseURL,
            path: "api/assistant/chat",
            method: "POST",
            token: token,
            body: ["message": message, "session_id": sessionID]
        )
        guard let object = try JSONSerialization.jsonObject(with: data) as? [String: Any] else {
            throw APIError.malformedPayload
        }
        let success = object["success"] as? Bool ?? false
        let intent = object["intent"] as? String ?? "unknown"
        let agent = object["agent"] as? String
        let message = object["message"] as? String
        let result = object["result"]
        let rawJSON = ReportRenderer.prettyJSON(from: object)
        let displayText = ReportRenderer.render(message: message, result: result, fallbackJSON: rawJSON)
        return AssistantChatPayload(
            success: success,
            intent: intent,
            agent: agent,
            message: message,
            result: result,
            displayText: displayText,
            rawJSON: rawJSON
        )
    }

    private static func requestData(
        baseURL: URL,
        path: String,
        method: String,
        token: String?,
        body: [String: Any]?
    ) async throws -> Data {
        let url = try makeURL(baseURL: baseURL, path: path)
        var request = URLRequest(url: url)
        request.httpMethod = method
        request.timeoutInterval = 120
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        if let token, !token.isEmpty {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        if let body {
            request.httpBody = try JSONSerialization.data(withJSONObject: body)
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        }

        let (data, response) = try await URLSession.shared.data(for: request)
        guard let http = response as? HTTPURLResponse else { throw APIError.invalidResponse }
        guard (200..<300).contains(http.statusCode) else {
            throw APIError.server(errorMessage(from: data, statusCode: http.statusCode))
        }
        return data
    }

    private static func makeURL(baseURL: URL, path: String) throws -> URL {
        guard var components = URLComponents(url: baseURL, resolvingAgainstBaseURL: false) else {
            throw APIError.invalidBaseURL
        }
        let basePath = components.path.trimmingCharacters(in: CharacterSet(charactersIn: "/"))
        let cleanPath = path.trimmingCharacters(in: CharacterSet(charactersIn: "/"))
        components.path = "/" + [basePath, cleanPath].filter { !$0.isEmpty }.joined(separator: "/")
        guard let url = components.url else { throw APIError.invalidBaseURL }
        return url
    }

    private static func errorMessage(from data: Data, statusCode: Int) -> String {
        guard
            let object = try? JSONSerialization.jsonObject(with: data),
            let dict = object as? [String: Any]
        else {
            return "请求失败：HTTP \(statusCode)"
        }
        if let message = dict["message"] as? String {
            return message
        }
        if let detail = dict["detail"] as? [String: Any] {
            if let message = detail["message"] as? String {
                return message
            }
            if let error = detail["error"] as? String {
                return error
            }
        }
        if let detail = dict["detail"] as? String {
            return detail
        }
        return "请求失败：HTTP \(statusCode)"
    }
}

extension JSONDecoder {
    static var api: JSONDecoder {
        JSONDecoder()
    }
}
