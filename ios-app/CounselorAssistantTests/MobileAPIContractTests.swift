import XCTest
@testable import CounselorAssistant

final class MobileAPIContractTests: XCTestCase {
    func testLoginResponseDecodesVersionedBearerContract() throws {
        let data = Data(#"""
        {
          "status":"success",
          "api_version":"v1",
          "access_token":"test-token",
          "token_type":"Bearer",
          "expires_at":"2026-07-10T10:00:00+00:00",
          "user":{"id":7,"username":"pilot","role":"counselor"}
        }
        """#.utf8)

        let response = try JSONDecoder().decode(LoginResponse.self, from: data)

        XCTAssertEqual(response.apiVersion, "v1")
        XCTAssertEqual(response.tokenType, "Bearer")
        XCTAssertEqual(response.user.role, "counselor")
    }

    func testCaseListDecodesDeidentifiedClientCode() throws {
        let data = Data(#"""
        {
          "status":"success",
          "cases":[{
            "id":1,"title":"Case A-001","client_code":"A001","notes":"",
            "created_at":"2026-07-03T10:00:00+00:00","updated_at":"2026-07-03T10:00:00+00:00"
          }]
        }
        """#.utf8)

        let response = try JSONDecoder().decode(CaseListResponse.self, from: data)

        XCTAssertEqual(response.cases.first?.clientCode, "A001")
    }

    func testAgentRunDecodesRouteOutputAndStructuredChecks() throws {
        let data = Data(#"""
        {
          "status":"success","case_id":1,"run_id":"run-W3-001",
          "detected_workflow_label":"Session record","route_status":"clear",
          "route_notice":"Automatically routed to a session record.",
          "clean_output":"本次咨询记录","structured_output":{"workflow":"W3"},
          "structured_check":{"status":"PASS"},"safety_check":{"status":"PASS"},"issues":[],
          "artifacts":[{"key":"docx","name":"output.docx","content_type":"application/vnd.openxmlformats-officedocument.wordprocessingml.document","download_path":"/api/mobile/v1/runs/run-W3-001/artifacts/docx"}]
        }
        """#.utf8)

        let response = try JSONDecoder().decode(AgentRunResponse.self, from: data)

        XCTAssertEqual(response.runID, "run-W3-001")
        XCTAssertEqual(response.detectedWorkflowLabel, "Session record")
        XCTAssertTrue(response.structuredOutput?.prettyPrinted.contains("W3") == true)
        XCTAssertEqual(response.artifacts.first?.key, "docx")
    }
}
