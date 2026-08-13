import Foundation

struct CounselorUser: Codable, Equatable, Identifiable {
    let id: Int
    let username: String
    let role: String
}

struct CounselorCase: Codable, Equatable, Identifiable {
    let id: Int
    let title: String
    let clientCode: String
    let notes: String
    let createdAt: String
    let updatedAt: String

    enum CodingKeys: String, CodingKey {
        case id, title, notes
        case clientCode = "client_code"
        case createdAt = "created_at"
        case updatedAt = "updated_at"
    }
}

struct LoginResponse: Codable {
    let status: String
    let apiVersion: String
    let accessToken: String
    let tokenType: String
    let expiresAt: String
    let user: CounselorUser

    enum CodingKeys: String, CodingKey {
        case status, user
        case apiVersion = "api_version"
        case accessToken = "access_token"
        case tokenType = "token_type"
        case expiresAt = "expires_at"
    }
}

struct SessionResponse: Codable {
    let status: String
    let authenticated: Bool
    let user: CounselorUser
}

struct CaseListResponse: Codable {
    let status: String
    let cases: [CounselorCase]
}

struct CaseMutationResponse: Codable {
    let status: String
    let counselorCase: CounselorCase

    enum CodingKeys: String, CodingKey {
        case status
        case counselorCase = "case"
    }
}

struct RecentRun: Codable, Equatable, Identifiable {
    let runID: String
    let workflow: String
    let createdAt: String?

    var id: String { runID }

    enum CodingKeys: String, CodingKey {
        case workflow
        case runID = "run_id"
        case createdAt = "created_at"
    }
}

struct CaseDetailResponse: Codable {
    let status: String
    let counselorCase: CounselorCase
    let recentRuns: [RecentRun]

    enum CodingKeys: String, CodingKey {
        case status
        case counselorCase = "case"
        case recentRuns = "recent_runs"
    }
}

struct AgentRunResponse: Codable {
    let status: String
    let caseID: Int
    let runID: String?
    let detectedWorkflowLabel: String
    let routeStatus: String?
    let routeNotice: String?
    let cleanOutput: String
    let structuredOutput: JSONValue?
    let structuredCheck: JSONValue?
    let safetyCheck: JSONValue?
    let issues: [JSONValue]
    let artifacts: [RunArtifact]

    enum CodingKeys: String, CodingKey {
        case status, issues, artifacts
        case caseID = "case_id"
        case runID = "run_id"
        case detectedWorkflowLabel = "detected_workflow_label"
        case routeStatus = "route_status"
        case routeNotice = "route_notice"
        case cleanOutput = "clean_output"
        case structuredOutput = "structured_output"
        case structuredCheck = "structured_check"
        case safetyCheck = "safety_check"
    }
}

struct RunArtifact: Codable, Equatable, Identifiable {
    let key: String
    let name: String
    let contentType: String
    let downloadPath: String

    var id: String { key }

    enum CodingKeys: String, CodingKey {
        case key, name
        case contentType = "content_type"
        case downloadPath = "download_path"
    }
}

struct CaseDeleteResponse: Codable {
    let status: String
    let deletedCaseID: Int
    let cases: [CounselorCase]

    enum CodingKeys: String, CodingKey {
        case status, cases
        case deletedCaseID = "deleted_case_id"
    }
}

enum JSONValue: Codable, Equatable {
    case string(String)
    case number(Double)
    case bool(Bool)
    case object([String: JSONValue])
    case array([JSONValue])
    case null

    init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()
        if container.decodeNil() {
            self = .null
        } else if let value = try? container.decode(Bool.self) {
            self = .bool(value)
        } else if let value = try? container.decode(Double.self) {
            self = .number(value)
        } else if let value = try? container.decode(String.self) {
            self = .string(value)
        } else if let value = try? container.decode([String: JSONValue].self) {
            self = .object(value)
        } else if let value = try? container.decode([JSONValue].self) {
            self = .array(value)
        } else {
            throw DecodingError.dataCorruptedError(in: container, debugDescription: "Unsupported JSON value")
        }
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.singleValueContainer()
        switch self {
        case .string(let value): try container.encode(value)
        case .number(let value): try container.encode(value)
        case .bool(let value): try container.encode(value)
        case .object(let value): try container.encode(value)
        case .array(let value): try container.encode(value)
        case .null: try container.encodeNil()
        }
    }

    var prettyPrinted: String {
        guard JSONSerialization.isValidJSONObject(foundationValue),
              let data = try? JSONSerialization.data(withJSONObject: foundationValue, options: [.prettyPrinted, .sortedKeys]),
              let text = String(data: data, encoding: .utf8) else {
            return String(describing: foundationValue)
        }
        return text
    }

    private var foundationValue: Any {
        switch self {
        case .string(let value): return value
        case .number(let value): return value
        case .bool(let value): return value
        case .object(let value): return value.mapValues(\.foundationValue)
        case .array(let value): return value.map(\.foundationValue)
        case .null: return NSNull()
        }
    }
}

struct APIErrorResponse: Codable {
    let status: String
    let code: String?
    let message: String
}
