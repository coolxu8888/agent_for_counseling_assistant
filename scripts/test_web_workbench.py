import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))

import web_workbench


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

    def test_handle_run_rejects_empty_input(self):
        response = web_workbench.handle_api_run({"workflow": "W1", "input": "   "})

        status, _headers, body = response
        self.assertEqual(status, 400)
        self.assertIn("Input is required", json.loads(body.decode("utf-8"))["message"])

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
            with patch.object(web_workbench, "run_agent_once", return_value=fake_result):
                status, _headers, body = web_workbench.handle_api_run(
                    {"workflow": "W1", "input": "材料", "structured": True, "render_docx": False}
                )

        payload = json.loads(body.decode("utf-8"))
        self.assertEqual(status, 200)
        self.assertEqual(payload["status"], "success")
        self.assertEqual(payload["workflow"], "W1")
        self.assertEqual(payload["clean_output"], "clean answer")
        self.assertEqual(payload["structured_output"], {"workflow": "W1"})
        self.assertEqual(payload["structured_check"], {"status": "PASS"})

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


if __name__ == "__main__":
    unittest.main()
