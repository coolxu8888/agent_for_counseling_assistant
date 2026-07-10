import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from w5_acceptance import (
    W5AcceptanceError,
    W5_REQUIRED_FIELDS,
    W5_TEMPLATE_PATH,
    W5_VISIBLE_LABEL,
    validate_hosted_report,
    validate_model_eval_report,
    validate_template_report,
    validate_web_report,
    write_sanitized_report,
)


def artifact():
    return {
        "format": "docx",
        "editable": True,
        "download_assertion": "passed",
        "filename": "w5-output.docx",
    }


def next_session_fields():
    return {
        "selected_framework": "CBT",
        "session_goal": ["Clarify one bounded goal for the next counseling session."],
        "focus_areas": ["Review the criticism-anxiety-avoidance cycle from last session."],
        "planned_interventions": ["Use guided review and one short cognitive restructuring practice."],
        "suggested_questions": ["What did you notice before deciding not to reply to colleagues?"],
        "risk_monitoring": ["Check ideation, intent, plan, means, and available support at the start."],
        "between_session_tasks": ["Optional self-monitoring note, only if counselor judges it appropriate."],
        "do_not_do": ["Do not expand into a multi-session roadmap or final treatment prescription."],
        "boundary_notes": ["Single-session plan only; counselor judgment and client consent are required."],
    }


def structured_result():
    return {"status": "PASS", "fields": next_session_fields()}


def valid_web_report():
    return {
        "report_type": "web",
        "base_url": "http://127.0.0.1:8766",
        "timestamp_utc": "2026-07-11T08:00:00Z",
        "scenario": {
            "workflow": "W5",
            "visible_label": W5_VISIBLE_LABEL,
            "route_status": "passed",
            "structured_result": structured_result(),
            "artifact": artifact(),
        },
    }


def valid_hosted_report():
    report = valid_web_report()
    report.update(
        report_type="hosted",
        base_url="https://counselor-agent-coze-api.onrender.com",
        deployed_version="abc1234",
    )
    report["scenario"].update(
        http_status=200,
        sanitized_input="De-identified W5 CBT next-session planning scenario.",
        model_run={"status": "success", "real_model": True, "provider": "deepseek", "model": "deepseek-chat"},
    )
    return report


def make_template_root():
    tmp = tempfile.TemporaryDirectory()
    root = Path(tmp.name)
    template = root / W5_TEMPLATE_PATH
    template.parent.mkdir(parents=True, exist_ok=True)
    template.write_bytes(b"fake docx identity for W5 acceptance contract")
    return tmp, root, template


def valid_template_report(root, template):
    return {
        "report_type": "template",
        "timestamp_utc": "2026-07-11T08:00:00Z",
        "workflow": "W5",
        "source_template": {
            "path": W5_TEMPLATE_PATH,
            "sha256": hashlib.sha256(template.read_bytes()).hexdigest(),
        },
        "fill": {"status": "PASS", "filled_fields": list(W5_REQUIRED_FIELDS), "unfilled_fields": [], "issues": []},
        "output_verification": {
            "status": "PASS",
            "reopened": True,
            "required_content": {field: f"verified W5 content for {field}" for field in W5_REQUIRED_FIELDS},
        },
    }


def valid_model_eval_report(root):
    summary = root / "eval-results" / "w5-api" / "eval-rubric-summary.v0.1.json"
    clean = root / "eval-results" / "w5-api" / "eval-clean-summary.v0.1.json"
    raw = root / "eval-results" / "w5-api" / "W5-001-deepseek-api-raw.txt"
    for path in (summary, clean, raw):
        path.parent.mkdir(parents=True, exist_ok=True)
    summary.write_text(
        json.dumps({"results": [{"id": "W5-001", "workflow": "workflow_5_next_session_plan", "status": "PASS"}]}),
        encoding="utf-8",
    )
    clean.write_text(json.dumps({"results": [{"id": "W5-001", "status": "PASS"}]}), encoding="utf-8")
    raw.write_text("W5 CBT next-session plan raw output", encoding="utf-8")
    return {
        "report_type": "real_model_eval",
        "timestamp_utc": "2026-07-11T08:00:00Z",
        "workflow": "W5",
        "eval_cases": ["W5-001"],
        "rubric_status": "PASS",
        "model_run": {"status": "success", "real_model": True, "provider": "deepseek", "model": "deepseek-chat"},
        "evidence": [
            {"type": "path", "value": "eval-results/w5-api/eval-rubric-summary.v0.1.json"},
            {"type": "path", "value": "eval-results/w5-api/eval-clean-summary.v0.1.json"},
            {"type": "path", "value": "eval-results/w5-api/W5-001-deepseek-api-raw.txt"},
        ],
        "structured_result": structured_result(),
    }


class W5AcceptanceTests(unittest.TestCase):
    def test_web_report_accepts_single_w5_next_session_scenario(self):
        validate_web_report(valid_web_report())

    def test_web_report_requires_w5_chinese_label_structured_fields_and_docx(self):
        report = valid_web_report()
        report["scenario"]["workflow"] = "W4"
        with self.assertRaisesRegex(W5AcceptanceError, "workflow"):
            validate_web_report(report)

        report = valid_web_report()
        report["scenario"]["visible_label"] = "Next-session plan"
        with self.assertRaisesRegex(W5AcceptanceError, "visible_label"):
            validate_web_report(report)

        report = valid_web_report()
        del report["scenario"]["structured_result"]["fields"]["risk_monitoring"]
        with self.assertRaisesRegex(W5AcceptanceError, "risk_monitoring"):
            validate_web_report(report)

        report = valid_web_report()
        report["scenario"]["structured_result"]["fields"]["selected_framework"] = "astrology"
        with self.assertRaisesRegex(W5AcceptanceError, "selected_framework"):
            validate_web_report(report)

        report = valid_web_report()
        report["scenario"]["artifact"]["editable"] = False
        with self.assertRaisesRegex(W5AcceptanceError, "editable"):
            validate_web_report(report)

    def test_hosted_report_requires_public_https_http_200_real_model_and_deployed_version(self):
        validate_hosted_report(valid_hosted_report())

        report = valid_hosted_report()
        report["base_url"] = "http://127.0.0.1:8766"
        with self.assertRaisesRegex(W5AcceptanceError, "public"):
            validate_hosted_report(report)

        report = valid_hosted_report()
        report["deployed_version"] = ""
        with self.assertRaisesRegex(W5AcceptanceError, "deployed_version"):
            validate_hosted_report(report)

        report = valid_hosted_report()
        report["scenario"]["model_run"]["real_model"] = False
        with self.assertRaisesRegex(W5AcceptanceError, "real-model"):
            validate_hosted_report(report)

    def test_template_report_requires_exact_template_hash_all_fields_and_reopened_output(self):
        tmp, root, template = make_template_root()
        with tmp:
            report = valid_template_report(root, template)
            validate_template_report(report, root)

            changed = json.loads(json.dumps(report))
            changed["source_template"]["path"] = "docs/other.docx"
            with self.assertRaisesRegex(W5AcceptanceError, "source_template.path"):
                validate_template_report(changed, root)

            changed = json.loads(json.dumps(report))
            changed["source_template"]["sha256"] = "0" * 64
            with self.assertRaisesRegex(W5AcceptanceError, "sha256"):
                validate_template_report(changed, root)

            changed = json.loads(json.dumps(report))
            changed["fill"]["filled_fields"] = ["selected_framework"]
            with self.assertRaisesRegex(W5AcceptanceError, "filled_fields"):
                validate_template_report(changed, root)

    def test_model_eval_report_requires_committed_w5_eval_paths_and_real_model(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report = valid_model_eval_report(root)
            validate_model_eval_report(report, root)

            changed = json.loads(json.dumps(report))
            changed["workflow"] = "W4"
            with self.assertRaisesRegex(W5AcceptanceError, "workflow"):
                validate_model_eval_report(changed, root)

            changed = json.loads(json.dumps(report))
            changed["evidence"][2]["value"] = "eval-results/w5-api/missing.txt"
            with self.assertRaisesRegex(W5AcceptanceError, "evidence"):
                validate_model_eval_report(changed, root)

            changed = json.loads(json.dumps(report))
            changed["model_run"]["real_model"] = False
            with self.assertRaisesRegex(W5AcceptanceError, "real-model"):
                validate_model_eval_report(changed, root)

    def test_reports_reject_secret_cookie_absolute_paths_jwts_and_non_finite_numbers(self):
        unsafe_values = [
            ("api_key", "redacted"),
            ("notes", "Authorization: Bearer private"),
            ("notes", "Cookie: session=private"),
            ("notes", "saved at /srv/app/private/output.docx"),
            ("notes", r"C:\\Users\\server\\output.docx"),
            ("notes", "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0In0.privatepart"),
        ]
        for key, value in unsafe_values:
            report = valid_web_report()
            report[key] = value
            with self.subTest(key=key, value=value):
                with self.assertRaises(W5AcceptanceError):
                    validate_web_report(report)

        report = valid_web_report()
        report["nested"] = {"score": float("nan")}
        with self.assertRaisesRegex(W5AcceptanceError, "finite"):
            validate_web_report(report)

    def test_writer_is_stable_and_rejects_non_finite_numbers(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "nested" / "report.json"
            report = valid_web_report()
            write_sanitized_report(path, report)
            first = path.read_bytes()
            write_sanitized_report(path, report)
            self.assertEqual(first, path.read_bytes())

            with self.assertRaises(W5AcceptanceError):
                write_sanitized_report(Path(directory) / "bad.json", {"value": float("inf")})


if __name__ == "__main__":
    unittest.main()
