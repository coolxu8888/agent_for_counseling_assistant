import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from w6_acceptance import (
    W6AcceptanceError,
    W6_REQUIRED_FIELDS,
    W6_TEMPLATE_PATH,
    W6_VISIBLE_LABEL,
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
        "filename": "w6-output.docx",
    }


def roadmap_fields():
    return {
        "selected_framework": "INTEGRATIVE",
        "overview": "Bounded, revisable roadmap for counselor planning.",
        "phases": ["Phase 1: engagement and assessment."],
        "hypotheses_to_verify": ["Criticism may activate shame and avoidance."],
        "session_focus_options": ["Next session: clarify the recent criticism trigger."],
        "risk_monitoring_checkpoints": ["Re-check ideation, self-harm, sleep, and supports at phase transitions."],
        "collaboration_or_referral_reminders": ["Consider referral only if new safety or medical concerns emerge."],
        "missing_information": ["Prior counseling response is not yet documented."],
        "do_not_do": ["Do not diagnose, promise outcomes, or prescribe a fixed protocol."],
        "boundary_notes": ["This is a revisable roadmap, not a diagnosis or rigid treatment plan."],
    }


def structured_result():
    return {"status": "PASS", "fields": roadmap_fields()}


def valid_web_report():
    return {
        "report_type": "web",
        "base_url": "http://127.0.0.1:8766",
        "timestamp_utc": "2026-07-19T08:00:00Z",
        "scenario": {
            "workflow": "W6",
            "visible_label": W6_VISIBLE_LABEL,
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
        sanitized_input="De-identified W6 integrative counseling roadmap scenario.",
        model_run={"status": "success", "real_model": True, "provider": "deepseek", "model": "deepseek-chat"},
    )
    return report


def make_template_root():
    tmp = tempfile.TemporaryDirectory()
    root = Path(tmp.name)
    template = root / W6_TEMPLATE_PATH
    template.parent.mkdir(parents=True, exist_ok=True)
    template.write_bytes(b"fake docx identity for W6 acceptance contract")
    return tmp, root, template


def valid_template_report(root, template):
    return {
        "report_type": "template",
        "timestamp_utc": "2026-07-19T08:00:00Z",
        "workflow": "W6",
        "source_template": {
            "path": W6_TEMPLATE_PATH,
            "sha256": hashlib.sha256(template.read_bytes()).hexdigest(),
        },
        "fill": {"status": "PASS", "filled_fields": list(W6_REQUIRED_FIELDS), "unfilled_fields": [], "issues": []},
        "output_verification": {
            "status": "PASS",
            "reopened": True,
            "required_content": {field: f"verified W6 content for {field}" for field in W6_REQUIRED_FIELDS},
        },
    }


def valid_model_eval_report(root):
    summary = root / "eval-results" / "w6-api" / "w6-pass-rubric-summary.v0.1.json"
    raw = root / "eval-results" / "w6-api" / "W6-001-deepseek-api-raw.txt"
    clean = root / "eval-results" / "w6-api" / "clean" / "W6-001-clean.md"
    for path in (summary, raw, clean):
        path.parent.mkdir(parents=True, exist_ok=True)
    summary.write_text(json.dumps([{"id": "W6-001", "status": "PASS", "rubric_status": "PASS"}]), encoding="utf-8")
    raw.write_text("W6 integrative counseling roadmap raw output", encoding="utf-8")
    clean.write_text("W6 clean roadmap output", encoding="utf-8")
    return {
        "report_type": "real_model_eval",
        "timestamp_utc": "2026-07-19T08:00:00Z",
        "workflow": "W6",
        "eval_cases": ["W6-001"],
        "rubric_status": "PASS",
        "model_run": {"status": "success", "real_model": True, "provider": "deepseek", "model": "deepseek-chat"},
        "evidence": [
            {"type": "path", "value": "eval-results/w6-api/w6-pass-rubric-summary.v0.1.json"},
            {"type": "path", "value": "eval-results/w6-api/W6-001-deepseek-api-raw.txt"},
            {"type": "path", "value": "eval-results/w6-api/clean/W6-001-clean.md"},
        ],
        "structured_result": structured_result(),
    }


class W6AcceptanceTests(unittest.TestCase):
    def test_web_report_accepts_single_w6_roadmap_scenario(self):
        validate_web_report(valid_web_report())

    def test_web_report_requires_w6_chinese_label_structured_fields_and_docx(self):
        report = valid_web_report()
        report["scenario"]["workflow"] = "W5"
        with self.assertRaisesRegex(W6AcceptanceError, "workflow"):
            validate_web_report(report)

        report = valid_web_report()
        report["scenario"]["visible_label"] = "Counseling roadmap"
        with self.assertRaisesRegex(W6AcceptanceError, "visible_label"):
            validate_web_report(report)

        report = valid_web_report()
        del report["scenario"]["structured_result"]["fields"]["risk_monitoring_checkpoints"]
        with self.assertRaisesRegex(W6AcceptanceError, "risk_monitoring_checkpoints"):
            validate_web_report(report)

        report = valid_web_report()
        report["scenario"]["structured_result"]["fields"]["selected_framework"] = "astrology"
        with self.assertRaisesRegex(W6AcceptanceError, "selected_framework"):
            validate_web_report(report)

        report = valid_web_report()
        report["scenario"]["artifact"]["editable"] = False
        with self.assertRaisesRegex(W6AcceptanceError, "editable"):
            validate_web_report(report)

    def test_hosted_report_requires_public_https_http_200_real_model_and_deployed_version(self):
        validate_hosted_report(valid_hosted_report())

        report = valid_hosted_report()
        report["scenario"]["structured_result"]["fields"]["overview"] = ["Revisable W6 roadmap overview."]
        validate_hosted_report(report)

        report = valid_hosted_report()
        report["base_url"] = "http://127.0.0.1:8766"
        with self.assertRaisesRegex(W6AcceptanceError, "public"):
            validate_hosted_report(report)

        report = valid_hosted_report()
        report["deployed_version"] = ""
        with self.assertRaisesRegex(W6AcceptanceError, "deployed_version"):
            validate_hosted_report(report)

        report = valid_hosted_report()
        report["scenario"]["model_run"]["real_model"] = False
        with self.assertRaisesRegex(W6AcceptanceError, "real-model"):
            validate_hosted_report(report)

    def test_template_report_requires_exact_template_hash_all_fields_and_reopened_output(self):
        tmp, root, template = make_template_root()
        with tmp:
            report = valid_template_report(root, template)
            validate_template_report(report, root)

            changed = json.loads(json.dumps(report))
            changed["source_template"]["path"] = "docs/other.docx"
            with self.assertRaisesRegex(W6AcceptanceError, "source_template.path"):
                validate_template_report(changed, root)

            changed = json.loads(json.dumps(report))
            changed["source_template"]["sha256"] = "0" * 64
            with self.assertRaisesRegex(W6AcceptanceError, "sha256"):
                validate_template_report(changed, root)

            changed = json.loads(json.dumps(report))
            changed["fill"]["filled_fields"] = ["selected_framework"]
            with self.assertRaisesRegex(W6AcceptanceError, "filled_fields"):
                validate_template_report(changed, root)

    def test_model_eval_report_requires_committed_w6_eval_paths_and_real_model(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report = valid_model_eval_report(root)
            validate_model_eval_report(report, root)

            changed = json.loads(json.dumps(report))
            changed["workflow"] = "W5"
            with self.assertRaisesRegex(W6AcceptanceError, "workflow"):
                validate_model_eval_report(changed, root)

            changed = json.loads(json.dumps(report))
            changed["evidence"][2]["value"] = "eval-results/w6-api/missing.txt"
            with self.assertRaisesRegex(W6AcceptanceError, "evidence"):
                validate_model_eval_report(changed, root)

            changed = json.loads(json.dumps(report))
            changed["model_run"]["real_model"] = False
            with self.assertRaisesRegex(W6AcceptanceError, "real-model"):
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
                with self.assertRaises(W6AcceptanceError):
                    validate_web_report(report)

        report = valid_web_report()
        report["nested"] = {"score": float("nan")}
        with self.assertRaisesRegex(W6AcceptanceError, "finite"):
            validate_web_report(report)

    def test_writer_is_stable_and_rejects_non_finite_numbers(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "nested" / "report.json"
            report = valid_web_report()
            write_sanitized_report(path, report)
            first = path.read_bytes()
            write_sanitized_report(path, report)
            self.assertEqual(first, path.read_bytes())

            with self.assertRaises(W6AcceptanceError):
                write_sanitized_report(Path(directory) / "bad.json", {"value": float("inf")})


if __name__ == "__main__":
    unittest.main()
