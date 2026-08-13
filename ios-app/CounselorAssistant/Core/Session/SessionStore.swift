import Foundation
import Combine

@MainActor
final class SessionStore: ObservableObject {
    @Published private(set) var user: CounselorUser?
    @Published private(set) var cases: [CounselorCase] = []
    @Published private(set) var isRestoring = true
    @Published private(set) var isWorking = false
    @Published var errorMessage: String?

    private let api: APIClient
    private let keychain: KeychainStore
    private var token: String?

    init(api: APIClient? = nil, keychain: KeychainStore = KeychainStore()) {
        self.keychain = keychain
        if let api {
            self.api = api
        } else {
            let rawURL = Bundle.main.object(forInfoDictionaryKey: "COUNSELOR_API_BASE_URL") as? String ?? ""
            let baseURL = URL(string: rawURL) ?? URL(string: "https://invalid.local/")!
            self.api = APIClient(baseURL: baseURL)
        }
    }

    func restoreSession() async {
        guard isRestoring else { return }
        defer { isRestoring = false }
        do {
            guard let storedToken = try keychain.loadToken() else { return }
            let response = try await api.currentSession(token: storedToken)
            token = storedToken
            user = response.user
            cases = try await api.cases(token: storedToken)
        } catch {
            try? keychain.deleteToken()
            token = nil
            user = nil
            cases = []
        }
    }

    func signIn(username: String, password: String) async {
        isWorking = true
        errorMessage = nil
        defer { isWorking = false }
        do {
            let response = try await api.login(username: username, password: password)
            try keychain.saveToken(response.accessToken)
            token = response.accessToken
            user = response.user
            cases = try await api.cases(token: response.accessToken)
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func refreshCases() async {
        guard let token else { return }
        do {
            cases = try await api.cases(token: token)
        } catch CounselorAPIError.authenticationRequired {
            await clearLocalSession()
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func createCase(title: String, clientCode: String) async -> Bool {
        guard let token else { return false }
        isWorking = true
        errorMessage = nil
        defer { isWorking = false }
        do {
            _ = try await api.createCase(title: title, clientCode: clientCode, token: token)
            cases = try await api.cases(token: token)
            return true
        } catch {
            errorMessage = error.localizedDescription
            return false
        }
    }

    func caseDetail(id: Int) async throws -> CaseDetailResponse {
        guard let token else { throw CounselorAPIError.authenticationRequired }
        return try await api.caseDetail(id: id, token: token)
    }

    func runAgent(caseID: Int, input: String) async throws -> AgentRunResponse {
        guard let token else { throw CounselorAPIError.authenticationRequired }
        return try await api.runAgent(caseID: caseID, input: input, token: token)
    }

    func runDetail(runID: String) async throws -> AgentRunResponse {
        guard let token else { throw CounselorAPIError.authenticationRequired }
        return try await api.runDetail(runID: runID, token: token)
    }

    func downloadArtifact(_ artifact: RunArtifact) async throws -> URL {
        guard let token else { throw CounselorAPIError.authenticationRequired }
        return try await api.downloadArtifact(artifact, token: token)
    }

    func deleteCase(id: Int) async -> Bool {
        guard let token else { return false }
        isWorking = true
        errorMessage = nil
        defer { isWorking = false }
        do {
            cases = try await api.deleteCase(id: id, token: token)
            return true
        } catch {
            errorMessage = error.localizedDescription
            return false
        }
    }

    func signOut() async {
        if let token {
            try? await api.logout(token: token)
        }
        await clearLocalSession()
    }

    private func clearLocalSession() async {
        try? keychain.deleteToken()
        token = nil
        user = nil
        cases = []
    }

    static var preview: SessionStore {
        SessionStore(api: APIClient(baseURL: URL(string: "https://example.invalid/")!))
    }
}
