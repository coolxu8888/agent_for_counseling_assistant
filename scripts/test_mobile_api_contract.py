import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))

import web_workbench
from workbench_store import WorkbenchStore


class MobileAPIContractTest(unittest.TestCase):
    def request_json(self, base_url, path, method="GET", payload=None, token=None):
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = Request(f"{base_url}{path}", data=body, method=method)
        request.add_header("Accept", "application/json")
        if body is not None:
            request.add_header("Content-Type", "application/json")
        if token:
            request.add_header("Authorization", f"Bearer {token}")
        try:
            with urlopen(request, timeout=5) as response:
                return response.status, dict(response.headers), json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            return exc.code, dict(exc.headers), json.loads(exc.read().decode("utf-8"))

    def test_login_session_and_case_list_over_http(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = WorkbenchStore(Path(tmp) / "workbench.sqlite3", Path(tmp) / "uploads")
            demo = store.authenticate("demo", "demo123")["user"]
            store.create_case(demo["id"], "Case A-001", client_code="A001")
            with patch.object(web_workbench, "STORE", store):
                with patch.object(web_workbench, "RUN_LOG_PATH", Path(tmp) / "run-log.jsonl"):
                    server = web_workbench.create_server(host="127.0.0.1", port=0)
                    thread = threading.Thread(target=server.serve_forever, daemon=True)
                    thread.start()
                    base_url = f"http://127.0.0.1:{server.server_address[1]}"
                    try:
                        status, headers, login = self.request_json(
                            base_url,
                            "/api/mobile/v1/login",
                            method="POST",
                            payload={"username": "demo", "password": "demo123"},
                        )
                        self.assertEqual(status, 200)
                        self.assertEqual(login["api_version"], "v1")
                        self.assertEqual(login["token_type"], "Bearer")
                        self.assertEqual(headers["Cache-Control"], "no-store")

                        token = login["access_token"]
                        status, _headers, session = self.request_json(
                            base_url, "/api/mobile/v1/session", token=token
                        )
                        self.assertEqual(status, 200)
                        self.assertTrue(session["authenticated"])

                        status, _headers, cases = self.request_json(
                            base_url, "/api/mobile/v1/cases", token=token
                        )
                        self.assertEqual(status, 200)
                        self.assertEqual(cases["cases"][0]["client_code"], "A001")

                        status, _headers, created = self.request_json(
                            base_url,
                            "/api/mobile/v1/cases",
                            method="POST",
                            payload={"action": "create", "title": "Case A-002", "client_code": "A002"},
                            token=token,
                        )
                        self.assertEqual(status, 201)
                        created_id = created["case"]["id"]

                        status, _headers, detail = self.request_json(
                            base_url, f"/api/mobile/v1/cases/{created_id}", token=token
                        )
                        self.assertEqual(status, 200)
                        self.assertEqual(detail["case"]["client_code"], "A002")
                        self.assertEqual(detail["recent_runs"], [])

                        run_dir = Path(tmp) / "run-W3-http"
                        run_dir.mkdir()
                        (run_dir / "clean_output.md").write_text("Session record", encoding="utf-8")
                        (run_dir / "structured_output.json").write_text('{"workflow":"W3"}', encoding="utf-8")
                        (run_dir / "output.docx").write_bytes(b"docx-http")
                        fake_result = web_workbench.AgentRunResult("W3", "success", run_dir)
                        with patch.object(web_workbench, "run_agent_once", return_value=fake_result):
                            status, _headers, run = self.request_json(
                                base_url,
                                "/api/mobile/v1/runs",
                                method="POST",
                                payload={"case_id": created_id, "input": "Write today's session record.", "workflow": "W1"},
                                token=token,
                            )
                        self.assertEqual(status, 200)
                        self.assertEqual(run["detected_workflow"], "W3")
                        self.assertEqual(run["run_id"], "run-W3-http")
                        self.assertNotIn("run_dir", run)
                        self.assertEqual(run["artifacts"][0]["key"], "docx")

                        status, _headers, reopened = self.request_json(
                            base_url, "/api/mobile/v1/runs/run-W3-http", token=token
                        )
                        self.assertEqual(status, 200)
                        self.assertEqual(reopened["clean_output"], "Session record")
                        self.assertNotIn("run_dir", reopened)

                        artifact_request = Request(
                            f"{base_url}/api/mobile/v1/runs/run-W3-http/artifacts/docx",
                            method="GET",
                        )
                        artifact_request.add_header("Authorization", f"Bearer {token}")
                        with urlopen(artifact_request, timeout=5) as artifact_response:
                            self.assertEqual(artifact_response.status, 200)
                            self.assertEqual(artifact_response.read(), b"docx-http")
                            self.assertEqual(artifact_response.headers["Cache-Control"], "no-store")

                        status, _headers, deleted = self.request_json(
                            base_url,
                            "/api/mobile/v1/cases",
                            method="POST",
                            payload={"action": "delete", "case_id": created_id, "confirm_case_id": created_id},
                            token=token,
                        )
                        self.assertEqual(status, 200)
                        self.assertEqual(deleted["deleted_case_id"], created_id)
                        self.assertFalse(run_dir.exists())
                    finally:
                        server.shutdown()
                        server.server_close()
                        thread.join(timeout=5)

    def test_mobile_case_list_rejects_missing_token(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = WorkbenchStore(Path(tmp) / "workbench.sqlite3", Path(tmp) / "uploads")
            with patch.object(web_workbench, "STORE", store):
                server = web_workbench.create_server(host="127.0.0.1", port=0)
                thread = threading.Thread(target=server.serve_forever, daemon=True)
                thread.start()
                try:
                    base_url = f"http://127.0.0.1:{server.server_address[1]}"
                    status, _headers, payload = self.request_json(base_url, "/api/mobile/v1/cases")
                    self.assertEqual(status, 401)
                    self.assertEqual(payload["api_version"], "v1")
                    self.assertEqual(payload["code"], "authentication_required")
                finally:
                    server.shutdown()
                    server.server_close()
                    thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
