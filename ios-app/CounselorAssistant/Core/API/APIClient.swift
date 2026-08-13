import Foundation

enum CounselorAPIError: LocalizedError {
    case invalidConfiguration
    case invalidResponse
    case authenticationRequired
    case server(String)

    var errorDescription: String? {
        switch self {
        case .invalidConfiguration:
            return "服务地址配置无效。"
        case .invalidResponse:
            return "服务器返回了无法识别的响应。"
        case .authenticationRequired:
            return "登录已失效，请重新登录。"
        case .server(let message):
            return message
        }
    }
}

final class APIClient {
    private let baseURL: URL
    private let session: URLSession
    private let decoder = JSONDecoder()
    private let encoder = JSONEncoder()

    init(baseURL: URL, session: URLSession = .shared) {
        self.baseURL = baseURL
        self.session = session
    }

    func login(username: String, password: String) async throws -> LoginResponse {
        var request = try makeRequest(path: "api/mobile/v1/login", method: "POST")
        request.httpBody = try encoder.encode(["username": username, "password": password])
        return try await send(request, as: LoginResponse.self)
    }

    func currentSession(token: String) async throws -> SessionResponse {
        let request = try makeRequest(path: "api/mobile/v1/session", token: token)
        return try await send(request, as: SessionResponse.self)
    }

    func cases(token: String) async throws -> [CounselorCase] {
        let request = try makeRequest(path: "api/mobile/v1/cases", token: token)
        let response = try await send(request, as: CaseListResponse.self)
        return response.cases
    }

    func createCase(title: String, clientCode: String, token: String) async throws -> CounselorCase {
        var request = try makeRequest(path: "api/mobile/v1/cases", method: "POST", token: token)
        request.httpBody = try encoder.encode(
            ["action": "create", "title": title, "client_code": clientCode]
        )
        let response = try await send(request, as: CaseMutationResponse.self)
        return response.counselorCase
    }

    func caseDetail(id: Int, token: String) async throws -> CaseDetailResponse {
        let request = try makeRequest(path: "api/mobile/v1/cases/\(id)", token: token)
        return try await send(request, as: CaseDetailResponse.self)
    }

    func runAgent(caseID: Int, input: String, token: String) async throws -> AgentRunResponse {
        var request = try makeRequest(path: "api/mobile/v1/runs", method: "POST", token: token)
        request.httpBody = try encoder.encode(
            ["case_id": String(caseID), "input": input]
        )
        return try await send(request, as: AgentRunResponse.self)
    }

    func runDetail(runID: String, token: String) async throws -> AgentRunResponse {
        let encoded = runID.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? runID
        let request = try makeRequest(path: "api/mobile/v1/runs/\(encoded)", token: token)
        return try await send(request, as: AgentRunResponse.self)
    }

    func deleteCase(id: Int, token: String) async throws -> [CounselorCase] {
        var request = try makeRequest(path: "api/mobile/v1/cases", method: "POST", token: token)
        request.httpBody = try encoder.encode(
            CaseDeleteRequest(action: "delete", caseID: id, confirmCaseID: id)
        )
        let response = try await send(request, as: CaseDeleteResponse.self)
        return response.cases
    }

    func downloadArtifact(_ artifact: RunArtifact, token: String) async throws -> URL {
        var request = try makeRequest(path: artifact.downloadPath, token: token)
        request.setValue(artifact.contentType, forHTTPHeaderField: "Accept")
        let (data, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse else {
            throw CounselorAPIError.invalidResponse
        }
        guard (200..<300).contains(http.statusCode) else {
            if http.statusCode == 401 { throw CounselorAPIError.authenticationRequired }
            if let apiError = try? decoder.decode(APIErrorResponse.self, from: data) {
                throw CounselorAPIError.server(apiError.message)
            }
            throw CounselorAPIError.invalidResponse
        }
        let folder = FileManager.default.temporaryDirectory.appendingPathComponent("CounselorAssistantArtifacts", isDirectory: true)
        try FileManager.default.createDirectory(at: folder, withIntermediateDirectories: true, attributes: nil)
        let safeName = artifact.name.replacingOccurrences(of: "/", with: "-")
        let destination = folder.appendingPathComponent("\(UUID().uuidString)-\(safeName)")
        try data.write(to: destination, options: .atomic)
        return destination
    }

    func logout(token: String) async throws {
        let request = try makeRequest(path: "api/mobile/v1/logout", method: "POST", token: token)
        _ = try await send(request, as: APIStatusResponse.self)
    }

    private func makeRequest(path: String, method: String = "GET", token: String? = nil) throws -> URLRequest {
        guard let url = URL(string: path, relativeTo: baseURL)?.absoluteURL else {
            throw CounselorAPIError.invalidConfiguration
        }
        var request = URLRequest(url: url)
        request.httpMethod = method
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        if method != "GET" {
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        }
        if let token {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        request.cachePolicy = .reloadIgnoringLocalCacheData
        request.timeoutInterval = 30
        return request
    }

    private func send<Response: Decodable>(_ request: URLRequest, as type: Response.Type) async throws -> Response {
        let (data, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse else {
            throw CounselorAPIError.invalidResponse
        }
        guard (200..<300).contains(http.statusCode) else {
            if http.statusCode == 401 {
                throw CounselorAPIError.authenticationRequired
            }
            if let apiError = try? decoder.decode(APIErrorResponse.self, from: data) {
                throw CounselorAPIError.server(apiError.message)
            }
            throw CounselorAPIError.invalidResponse
        }
        do {
            return try decoder.decode(type, from: data)
        } catch {
            throw CounselorAPIError.invalidResponse
        }
    }
}

private struct CaseDeleteRequest: Encodable {
    let action: String
    let caseID: Int
    let confirmCaseID: Int

    enum CodingKeys: String, CodingKey {
        case action
        case caseID = "case_id"
        case confirmCaseID = "confirm_case_id"
    }
}

private struct APIStatusResponse: Codable {
    let status: String
}
