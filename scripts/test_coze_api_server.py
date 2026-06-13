import json
import os
import sys
import tempfile
import unittest
import base64
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))

import coze_api_server


class FakeHandler:
    def __init__(self, headers=None):
        self.headers = headers or {"Host": "127.0.0.1:8770"}


class CozeApiServerTest(unittest.TestCase):
    def test_openapi_spec_contains_two_tool_operations(self):
        spec = coze_api_server.openapi_spec("https://example.test")

        self.assertEqual(spec["servers"][0]["url"], "https://example.test/coze")
        self.assertIn("/run_workflow", spec["paths"])
        self.assertIn("/draft_template", spec["paths"])
        self.assertEqual(
            spec["paths"]["/run_workflow"]["post"]["operationId"],
            "run_workflow",
        )
        self.assertEqual(
            spec["paths"]["/draft_template"]["post"]["operationId"],
            "draft_template",
        )

    def test_openapi_tool_responses_define_json_object_schema(self):
        spec = coze_api_server.openapi_spec("https://example.test")

        for path in ["/run_workflow", "/draft_template"]:
            schema = spec["paths"][path]["post"]["responses"]["200"]["content"]["application/json"]["schema"]

            self.assertEqual(schema["type"], "object")
            self.assertIn("answer", schema["properties"])
            self.assertIn("artifacts", schema["properties"])
            self.assertEqual(schema["properties"]["artifacts"]["type"], "array")

    def test_service_info_exposes_openapi_and_tool_urls(self):
        info = coze_api_server.service_info("https://example.test")

        self.assertEqual(info["status"], "ok")
        self.assertEqual(info["openapi"], "https://example.test/openapi.json")
        self.assertEqual(
            info["tools"][0]["url"],
            "https://example.test/coze/run_workflow",
        )
        self.assertEqual(
            info["tools"][1]["url"],
            "https://example.test/coze/draft_template",
        )

    def test_artifact_url_uses_request_host(self):
        handler = FakeHandler({"Host": "demo.local", "X-Forwarded-Proto": "https"})

        url = coze_api_server.artifact_url(handler, r"C:\runs\output.docx")

        self.assertTrue(url.startswith("https://demo.local/files/"))
        self.assertIn("output.docx", url)

    def test_build_run_workflow_response_includes_answer_and_docx_artifact(self):
        handler = FakeHandler()
        payload = {
            "status": "success",
            "workflow": "W3",
            "run_dir": r"C:\runs\run1",
            "clean_output": "咨询记录正文",
            "structured_output": {"workflow": "W3"},
            "docx": {"path": r"C:\runs\run1\output.docx", "status": "PASS"},
            "issues": [],
        }

        result = coze_api_server.build_run_workflow_response(handler, payload)

        self.assertEqual(result["answer"], "咨询记录正文")
        self.assertEqual(result["workflow"], "W3")
        self.assertEqual(result["artifacts"][0]["name"], "output.docx")
        self.assertIn("/files/", result["artifacts"][0]["url"])

    def test_build_draft_template_response_summarizes_report(self):
        handler = FakeHandler()
        payload = {
            "status": "success",
            "run_dir": r"C:\runs\tpl",
            "output_path": r"C:\runs\tpl\filled_template.docx",
            "draft_path": r"C:\runs\tpl\template_draft.json",
            "report_path": r"C:\runs\tpl\template_fill_report.json",
            "report": {
                "filled_fields": [{"template_label": "主要困扰"}],
                "kept_fields": [{"template_label": "签名"}],
                "skipped_fields": [],
                "issues": [{"level": "WARN", "message": "risk"}],
            },
        }

        result = coze_api_server.build_draft_template_response(handler, payload)

        self.assertIn("填充 1 项", result["answer"])
        self.assertEqual(len(result["artifacts"]), 3)
        self.assertEqual(result["artifacts"][0]["kind"], "docx")

    def test_handle_coze_run_workflow_wraps_backend_success(self):
        handler = FakeHandler()
        backend_payload = {
            "status": "success",
            "workflow": "W3",
            "run_dir": r"C:\runs\run1",
            "clean_output": "记录",
            "structured_output": {"workflow": "W3"},
            "docx": {"path": r"C:\runs\run1\output.docx"},
            "issues": [],
        }

        with patch.object(coze_api_server, "handle_api_run", return_value=coze_api_server.json_response(backend_payload)) as fake:
            status, _headers, body = coze_api_server.handle_coze_run_workflow(
                {"input": "材料", "workflow": "W3"},
                handler,
            )

        result = json.loads(body.decode("utf-8"))
        self.assertEqual(status, 200)
        self.assertEqual(result["answer"], "记录")
        self.assertTrue(fake.call_args.args[0]["render_docx"])

    def test_handle_coze_draft_template_wraps_backend_success(self):
        handler = FakeHandler()
        backend_payload = {
            "status": "success",
            "run_dir": r"C:\runs\tpl",
            "output_path": r"C:\runs\tpl\filled_template.docx",
            "draft_path": r"C:\runs\tpl\template_draft.json",
            "report_path": r"C:\runs\tpl\template_fill_report.json",
            "report": {"filled_fields": [], "kept_fields": [], "skipped_fields": [], "issues": []},
        }

        with patch.object(coze_api_server, "handle_draft_template", return_value=coze_api_server.json_response(backend_payload)):
            status, _headers, body = coze_api_server.handle_coze_draft_template(
                {"template_path": "template.docx", "raw_input": "材料"},
                handler,
            )

        result = json.loads(body.decode("utf-8"))
        self.assertEqual(status, 200)
        self.assertEqual(result["status"], "success")
        self.assertEqual(len(result["artifacts"]), 3)

    def test_save_template_base64_writes_uploaded_template_inside_run_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_root = Path(tmp) / "agent-runs"
            encoded = base64.b64encode(b"docx-bytes").decode("ascii")

            with patch.object(coze_api_server, "RUN_ROOT", run_root):
                path, run_dir = coze_api_server.save_template_base64(encoded, "咨询模板.docx")

            self.assertTrue(path.exists())
            self.assertEqual(path.read_bytes(), b"docx-bytes")
            self.assertTrue(str(path).endswith(".docx"))
            self.assertIn("COZE-TEMPLATE", str(run_dir))

    def test_save_template_base64_rejects_invalid_content(self):
        with self.assertRaisesRegex(ValueError, "valid base64"):
            coze_api_server.save_template_base64("not base64 !", "template.docx")

    def test_handle_coze_draft_template_accepts_template_base64(self):
        handler = FakeHandler()
        backend_payload = {
            "status": "success",
            "run_dir": r"C:\runs\tpl",
            "output_path": r"C:\runs\tpl\filled_template.docx",
            "draft_path": r"C:\runs\tpl\template_draft.json",
            "report_path": r"C:\runs\tpl\template_fill_report.json",
            "report": {"filled_fields": [], "kept_fields": [], "skipped_fields": [], "issues": []},
        }
        encoded = base64.b64encode(b"docx-bytes").decode("ascii")

        with tempfile.TemporaryDirectory() as tmp:
            run_root = Path(tmp) / "agent-runs"
            with patch.object(coze_api_server, "RUN_ROOT", run_root):
                with patch.object(coze_api_server, "handle_draft_template", return_value=coze_api_server.json_response(backend_payload)) as fake:
                    status, _headers, body = coze_api_server.handle_coze_draft_template(
                        {
                            "template_base64": encoded,
                            "template_filename": "template.docx",
                            "raw_input": "材料",
                        },
                        handler,
                    )

        result = json.loads(body.decode("utf-8"))
        self.assertEqual(status, 200)
        self.assertEqual(result["status"], "success")
        self.assertIn("template.docx", fake.call_args.args[0]["template_path"])

    def test_auth_allows_local_without_configured_key(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertTrue(coze_api_server.is_authorized(FakeHandler({})))

    def test_auth_requires_matching_key_when_configured(self):
        with patch.dict(os.environ, {"COZE_DEMO_API_KEY": "secret"}, clear=True):
            self.assertFalse(coze_api_server.is_authorized(FakeHandler({})))
            self.assertTrue(coze_api_server.is_authorized(FakeHandler({"X-API-Key": "secret"})))
            self.assertTrue(coze_api_server.is_authorized(FakeHandler({"Authorization": "Bearer secret"})))

    def test_write_openapi_writes_json_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "openapi.json"

            written = coze_api_server.write_openapi(target, base_url="https://example.test")

            data = json.loads(written.read_text(encoding="utf-8"))
        self.assertEqual(data["servers"][0]["url"], "https://example.test/coze")


if __name__ == "__main__":
    unittest.main()
