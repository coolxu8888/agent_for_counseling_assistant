import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from urllib.parse import quote
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))

import web_workbench
from workbench_store import WorkbenchStore


WORD_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def write_test_docx(path, document_xml):
    with zipfile.ZipFile(path, "w") as package:
        package.writestr("[Content_Types].xml", "")
        package.writestr("word/document.xml", document_xml)


class WebWorkbenchTest(unittest.TestCase):
    def test_json_response_encodes_utf8_payload(self):
        status, headers, body = web_workbench.json_response({"message": "咨询师助理"})

        self.assertEqual(status, 200)
        self.assertEqual(headers["Content-Type"], "application/json; charset=utf-8")
        self.assertEqual(json.loads(body.decode("utf-8")), {"message": "咨询师助理"})

    def test_error_response_uses_error_shape(self):
        status, headers, body = web_workbench.error_response(400, "Missing input")

        self.assertEqual(status, 400)
        self.assertEqual(headers["Content-Type"], "application/json; charset=utf-8")
        self.assertEqual(
            json.loads(body.decode("utf-8")),
            {"status": "error", "message": "Missing input"},
        )

    def test_static_file_path_resolves_inside_web_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            web_root = Path(tmp) / "web-workbench"
            web_root.mkdir()
            index_path = web_root / "index.html"
            index_path.write_text("<h1>ok</h1>", encoding="utf-8")

            resolved = web_workbench.resolve_static_path("/", web_root)

        self.assertEqual(resolved.name, "index.html")

    def test_resolve_download_path_allows_agent_runs_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_root = root / "agent-runs"
            run_root.mkdir()
            output = run_root / "file.docx"
            output.write_bytes(b"docx")

            resolved = web_workbench.resolve_download_path(str(output), allowed_roots=[run_root])

        self.assertEqual(resolved.name, "file.docx")

    def test_resolve_download_path_rejects_outside_agent_runs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_root = root / "agent-runs"
            run_root.mkdir()
            outside = root / "secret.txt"
            outside.write_text("secret", encoding="utf-8")

            with self.assertRaises(ValueError):
                web_workbench.resolve_download_path(str(outside), allowed_roots=[run_root])

    def test_safe_content_disposition_includes_unicode_filename_star(self):
        header = web_workbench.safe_content_disposition("报告.docx")

        self.assertIn('filename="__.docx"', header)
        self.assertIn("filename*=UTF-8''%E6%8A%A5%E5%91%8A.docx", header)
        header.encode("ascii")

    def test_safe_content_disposition_sanitizes_unsafe_fallback_characters(self):
        header = web_workbench.safe_content_disposition('bad";\r\nname.docx')
        fallback = header.split("filename=", 1)[1].split(";", 1)[0]

        self.assertNotIn('"', fallback.strip('"'))
        self.assertNotIn(";", fallback)
        self.assertNotIn("\r", fallback)
        self.assertNotIn("\n", fallback)
        header.encode("ascii")

    def test_handle_file_download_uses_filename_star_for_unicode_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_root = root / "agent-runs"
            run_root.mkdir()
            output = run_root / "报告.docx"
            output.write_bytes(b"docx")
            request_path = "/files/" + quote(str(output), safe="")

            with patch.object(web_workbench, "RUN_ROOT", run_root):
                status, headers, body = web_workbench.handle_file_download(request_path)

        self.assertEqual(status, 200)
        self.assertEqual(body, b"docx")
        self.assertIn("filename*", headers["Content-Disposition"])
        self.assertIn("%E6%8A%A5%E5%91%8A.docx", headers["Content-Disposition"])
        headers["Content-Disposition"].encode("ascii")

    def test_handle_run_rejects_empty_input(self):
        response = web_workbench.handle_api_run({"workflow": "W1", "input": "   "})

        status, _headers, body = response
        self.assertEqual(status, 400)
        self.assertIn("Input is required", json.loads(body.decode("utf-8"))["message"])

    def test_handle_login_sets_session_cookie(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = WorkbenchStore(Path(tmp) / "workbench.sqlite3", Path(tmp) / "uploads")
            with patch.object(web_workbench, "STORE", store):
                status, headers, body = web_workbench.handle_login(
                    {"username": "demo", "password": "demo123"}
                )

        payload = json.loads(body.decode("utf-8"))
        self.assertEqual(status, 200)
        self.assertEqual(payload["status"], "success")
        self.assertIn("Set-Cookie", headers)
        self.assertIn(web_workbench.SESSION_COOKIE, headers["Set-Cookie"])

    def test_apply_output_style_adds_style_instruction(self):
        styled = web_workbench.apply_output_style("材料", style="warm_clinical")

        self.assertIn("材料", styled)
        self.assertIn("输出风格要求", styled)
        self.assertIn("温和", styled)

    def test_apply_output_style_leaves_default_input_unchanged(self):
        self.assertEqual(web_workbench.apply_output_style("材料", style="default"), "材料")

    def test_handle_run_returns_saved_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "agent-runs" / "run-1"
            run_dir.mkdir(parents=True)
            (run_dir / "clean_output.md").write_text("clean answer", encoding="utf-8")
            (run_dir / "structured_output.json").write_text('{"workflow": "W1"}', encoding="utf-8")
            (run_dir / "structured_check.json").write_text('{"status": "PASS"}', encoding="utf-8")
            (run_dir / "safety_check.json").write_text(
                '{"status": "PASS", "rubric_status": "PASS"}',
                encoding="utf-8",
            )
            (run_dir / "metadata.json").write_text('{"status": "success"}', encoding="utf-8")

            fake_result = web_workbench.AgentRunResult("W1", "success", run_dir)
            with patch.object(web_workbench, "run_agent_once", return_value=fake_result) as fake_run:
                status, _headers, body = web_workbench.handle_api_run(
                    {
                        "workflow": "W1",
                        "input": "材料",
                        "structured": True,
                        "render_docx": False,
                        "output_style": "institutional_record",
                    }
                )

        payload = json.loads(body.decode("utf-8"))
        self.assertEqual(status, 200)
        self.assertEqual(payload["status"], "success")
        self.assertEqual(payload["workflow"], "W1")
        self.assertEqual(payload["clean_output"], "clean answer")
        self.assertEqual(payload["structured_output"], {"workflow": "W1"})
        self.assertEqual(payload["structured_check"], {"status": "PASS"})
        self.assertIn("机构留档", fake_run.call_args.kwargs["inline_input"])

    def test_handle_run_rejects_unknown_workflow(self):
        with patch.object(
            web_workbench,
            "run_agent_once",
            side_effect=web_workbench.AgentInputError("Unknown workflow `bad`."),
        ):
            status, _headers, body = web_workbench.handle_api_run({"workflow": "bad", "input": "材料"})

        payload = json.loads(body.decode("utf-8"))
        self.assertEqual(status, 400)
        self.assertEqual(payload["message"], "Unknown workflow `bad`.")

    def test_handle_run_hides_unexpected_exception_details(self):
        with patch.object(
            web_workbench,
            "run_agent_once",
            side_effect=RuntimeError("secret provider token"),
        ):
            status, _headers, body = web_workbench.handle_api_run({"workflow": "W1", "input": "材料"})

        payload = json.loads(body.decode("utf-8"))
        self.assertEqual(status, 500)
        self.assertEqual(payload["message"], "Agent run failed.")
        self.assertNotIn("secret provider token", body.decode("utf-8"))

    def test_load_run_payload_tolerates_malformed_json_artifact(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "agent-runs" / "run-1"
            run_dir.mkdir(parents=True)
            (run_dir / "clean_output.md").write_text("clean answer", encoding="utf-8")
            (run_dir / "structured_output.json").write_text("{not valid json", encoding="utf-8")

            result = web_workbench.AgentRunResult("W1", "success", run_dir)
            payload = web_workbench.load_run_payload(result)

        self.assertEqual(payload["status"], "success")
        self.assertEqual(payload["clean_output"], "clean answer")
        self.assertIsNone(payload["structured_output"])
        self.assertTrue(
            any("structured_output.json" in issue["message"] for issue in payload["issues"]),
            payload["issues"],
        )

    def test_handle_render_docx_requires_structured_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_root = Path(tmp) / "agent-runs"
            run_dir = run_root / "run"
            run_dir.mkdir(parents=True)
            with patch.object(web_workbench, "RUN_ROOT", run_root):
                status, _headers, body = web_workbench.handle_render_docx({"run_dir": str(run_dir)})

        self.assertEqual(status, 400)
        self.assertIn("structured_output.json", json.loads(body.decode("utf-8"))["message"])

    def test_handle_render_docx_rejects_run_dir_outside_run_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_root = Path(tmp) / "agent-runs"
            run_root.mkdir()
            run_dir = Path(tmp) / "outside-run"
            run_dir.mkdir()
            (run_dir / "structured_output.json").write_text('{"workflow": "W1"}', encoding="utf-8")

            with patch.object(web_workbench, "RUN_ROOT", run_root):
                status, _headers, body = web_workbench.handle_render_docx({"run_dir": str(run_dir)})

        payload = json.loads(body.decode("utf-8"))
        self.assertEqual(status, 400)
        self.assertIn("outside approved output directory", payload["message"])

    def test_handle_fill_template_uses_current_structured_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_root = Path(tmp) / "agent-runs"
            run_dir = run_root / "run"
            run_dir.mkdir(parents=True)
            structured = run_dir / "structured_output.json"
            structured.write_text('{"workflow": "W1"}', encoding="utf-8")
            template = Path(tmp) / "template.docx"
            template.write_bytes(b"fake docx")

            def fake_fill(template_path, structured_path, output_path, report_path, mapping_path=None):
                Path(output_path).write_bytes(b"filled")
                report = {"status": "PASS", "filled_fields": [{"template_label": "A"}], "unfilled_fields": [], "issues": []}
                Path(report_path).write_text(json.dumps(report), encoding="utf-8")
                return report

            with patch.object(web_workbench, "fill_docx_template", side_effect=fake_fill):
                with patch.object(web_workbench, "RUN_ROOT", run_root):
                    status, _headers, body = web_workbench.handle_fill_template(
                        {"run_dir": str(run_dir), "template_path": str(template)}
                    )

        payload = json.loads(body.decode("utf-8"))
        self.assertEqual(status, 200)
        self.assertEqual(payload["status"], "success")
        self.assertTrue(payload["output_path"].endswith("filled_template.docx"))
        self.assertEqual(payload["report"]["status"], "PASS")

    def test_handle_draft_template_requires_raw_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            template = Path(tmp) / "template.docx"
            template.write_bytes(b"fake docx")

            status, _headers, body = web_workbench.handle_draft_template(
                {"template_path": str(template), "raw_input": "   "}
            )

        self.assertEqual(status, 400)
        self.assertIn("Raw input is required", json.loads(body.decode("utf-8"))["message"])

    def test_handle_draft_template_creates_standalone_run_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_root = root / "agent-runs"
            template = root / "template.docx"
            template.write_bytes(b"fake docx")

            def fake_fill(
                template_path,
                raw_input,
                output_path,
                report_path,
                draft_path,
                style="professional_concise",
                custom_style="",
                existing_content_policy="merge",
            ):
                Path(output_path).write_bytes(b"filled")
                Path(draft_path).write_text('{"drafts": []}', encoding="utf-8")
                report = {
                    "status": "PASS",
                    "filled_fields": [{"template_label": "主要困扰"}],
                    "unfilled_fields": [],
                    "issues": [],
                    "existing_content_policy": existing_content_policy,
                }
                Path(report_path).write_text(json.dumps(report), encoding="utf-8")
                return report

            with patch.object(web_workbench, "RUN_ROOT", run_root):
                with patch.object(web_workbench, "fill_docx_template_from_raw", side_effect=fake_fill):
                    status, _headers, body = web_workbench.handle_draft_template(
                        {
                            "template_path": str(template),
                            "raw_input": "来访者分手后情绪低落。",
                            "style": "warm_clinical",
                            "existing_content_policy": "merge",
                        }
                    )

        payload = json.loads(body.decode("utf-8"))
        self.assertEqual(status, 200)
        self.assertEqual(payload["status"], "success")
        self.assertIn("TEMPLATE", payload["run_dir"])
        self.assertTrue(payload["output_path"].endswith("filled_template.docx"))
        self.assertTrue(payload["draft_path"].endswith("template_draft.json"))
        self.assertEqual(payload["report"]["existing_content_policy"], "merge")

    def test_handle_draft_template_rejects_run_dir_outside_run_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_root = root / "agent-runs"
            run_root.mkdir()
            outside = root / "outside"
            outside.mkdir()
            template = root / "template.docx"
            template.write_bytes(b"fake docx")

            with patch.object(web_workbench, "RUN_ROOT", run_root):
                status, _headers, body = web_workbench.handle_draft_template(
                    {
                        "template_path": str(template),
                        "raw_input": "材料",
                        "run_dir": str(outside),
                    }
                )

        payload = json.loads(body.decode("utf-8"))
        self.assertEqual(status, 400)
        self.assertIn("outside approved output directory", payload["message"])

    def test_handle_inspect_template_returns_slots_and_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            template = Path(tmp) / "template.docx"
            write_test_docx(
                template,
                (
                    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                    f'<w:document xmlns:w="{WORD_NS}">'
                    "<w:body>"
                    "<w:tbl>"
                    "<w:tr>"
                    "<w:tc><w:p><w:r><w:t>主要困扰</w:t></w:r></w:p></w:tc>"
                    "<w:tc><w:p><w:r><w:t>____</w:t></w:r></w:p></w:tc>"
                    "</w:tr>"
                    "<w:tr>"
                    "<w:tc><w:p><w:r><w:t>已有理解</w:t></w:r></w:p></w:tc>"
                    "<w:tc><w:p><w:r><w:t>原有内容</w:t></w:r></w:p></w:tc>"
                    "</w:tr>"
                    "</w:tbl>"
                    "<w:sectPr/>"
                    "</w:body>"
                    "</w:document>"
                ),
            )

            status, _headers, body = web_workbench.handle_inspect_template(
                {"template_path": str(template)}
            )

        payload = json.loads(body.decode("utf-8"))
        self.assertEqual(status, 200)
        self.assertEqual(payload["status"], "success")
        self.assertEqual(payload["summary"]["total_slots"], 2)
        self.assertEqual(payload["summary"]["fillable_slots"], 1)
        self.assertEqual(payload["summary"]["prefilled_slots"], 1)
        self.assertEqual(payload["slots"][0]["label"], "主要困扰")


if __name__ == "__main__":
    unittest.main()
