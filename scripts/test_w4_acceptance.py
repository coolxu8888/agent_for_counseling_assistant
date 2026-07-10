import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from w4_acceptance import (
    W4AcceptanceError,
    W4_REQUIRED_FIELDS,
    W4_TEMPLATE_PATH,
    W4_VISIBLE_LABEL,
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
        "filename": "w4-output.docx",
    }


def conceptualization_fields():
    return {
        "selected_framework": "CBT",
        "known_facts": ["Client becomes anxious before performance reviews."],
        "presenting_patterns": ["Criticism-anxiety-avoidance cycle."],
        "predisposing_factors": ["Family comparison history may shape threat sensitivity."],
        "precipitating_factors": ["Recent supervisor conflict and poor sleep."],
        "maintaining_factors": ["Avoiding colleagues reduces corrective feedback."],
        "protective_factors": ["Client denies suicide plan and seeks counseling."],
        "risk_considerations": ["Continue checking ideation, intent, plan, means, and supports."],
        "working_hypotheses": ["Performance evaluation may activate inadequacy beliefs."],
        "questions_to_verify": ["What evidence does the client use when predicting criticism?"],
        "boundary_notes": ["This is a working hypothesis, not a diagnosis or treatment plan."],
    }


def structured_result():
    return {"status": "PASS", "fields": conceptualization_fields()}


def valid_web_report():
    return {
        "report_type": "web",
        "base_url": "http://127.0.0.1:8766",
        "timestamp_utc": "2026-07-11T08:00:00Z",
        "scenario": {
            "workflow": "W4",
            "visible_label": W4_VISIBLE_LABEL,
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
        sanitized_input="De-identified W4 CBT case conceptualization scenario.",
        model_run={"status": "success", "real_model": True, "provider": "deepseek", "model": "deepseek-chat"},
    )
    return report


def make_template_root():
    tmp = tempfile.TemporaryDirectory()
    root = Path(tmp.name)
    template = root / W4_TEMPLATE_PATH
    template.parent.mkdir(parents=True, exist_ok=True)
    template.write_bytes(b"fake docx identity for W4 acceptance contract")
    return tmp, root, template


def valid_template_report(root, template):
    return {
        "report_type": "template",
        "timestamp_utc": "2026-07-11T08:00:00Z",
        "workflow": "W4",
        "source_template": {
            "path": W4_TEMPLATE_PATH,
            "sha256": hashlib.sha256(template.read_bytes()).hexdigest(),
        },
        "fill": {"status": "PASS", "filled_fields": list(W4_REQUIRED_FIELDS), "unfilled_fields": [], "issues": []},
        "output_verification": {
            "status": "PASS",
            "reopened": True,
            "required_content": {field: f"verified W4 content for {field}" for field in W4_REQUIRED_FIELDS},
        },
    }


def valid_model_eval_report(root):
    summary = root / "eval-results" / "eval-rubric-summary.v0.1.json"
    clean = root / "eval-results" / "eval-clean-summary.v0.1.json"
    raw = root / "eval-results" / "W4-001-deepseek-raw.txt"
    for path in (summary, clean, raw):
        path.parent.mkdir(parents=True, exist_ok=True)
    summary.write_text(
        json.dumps({"results": [{"id": "W4-001", "workflow": "workflow_4_case_conceptualization", "status": "PASS"}]}),
        encoding="utf-8",
    )
    clean.write_text(json.dumps({"results": [{"id": "W4-001", "status": "PASS"}]}), encoding="utf-8")
    raw.write_text("W4 CBT case conceptualization raw output", encoding="utf-8")
    return {
        "report_type": "real_model_eval",
        "timestamp_utc": "2026-07-11T08:00:00Z",
        "workflow": "W4",
        "eval_cases": ["W4-001"],
        "rubric_status": "PASS",
        "model_run": {"status": "success", "real_model": True, "provider": "deepseek", "model": "deepseek-chat"},
        "evidence": [
            {"type": "path", "value": "eval-results/eval-rubric-summary.v0.1.json"},
            {"type": "path", "value": "eval-results/eval-clean-summary.v0.1.json"},
            {"type": "path", "value": "eval-results/W4-001-deepseek-raw.txt"},
        ],
        "structured_result": structured_result(),
    }


class W4AcceptanceTests(unittest.TestCase):
    def test_web_report_accepts_single_w4_conceptualization_scenario(self):
        validate_web_report(valid_web_report())

    def test_web_report_requires_w4_chinese_label_structured_fields_and_docx(self):
        report = valid_web_report()
        report["scenario"]["workflow"] = "W3"
        with self.assertRaisesRegex(W4AcceptanceError, "workflow"):
            validate_web_report(report)

        report = valid_web_report()
        report["scenario"]["visible_label"] = "Conceptualization"
        with self.assertRaisesRegex(W4AcceptanceError, "visible_label"):
            validate_web_report(report)

        report = valid_web_report()
        del report["scenario"]["structured_result"]["fields"]["working_hypotheses"]
        with self.assertRaisesRegex(W4AcceptanceError, "working_hypotheses"):
            validate_web_report(report)

        report = valid_web_report()
        report["scenario"]["structured_result"]["fields"]["selected_framework"] = "astrology"
        with self.assertRaisesRegex(W4AcceptanceError, "selected_framework"):
            validate_web_report(report)

        report = valid_web_report()
        report["scenario"]["artifact"]["editable"] = False
        with self.assertRaisesRegex(W4AcceptanceError, "editable"):
            validate_web_report(report)

    def test_hosted_report_requires_public_https_http_200_real_model_and_deployed_version(self):
        validate_hosted_report(valid_hosted_report())

        report = valid_hosted_report()
        report["base_url"] = "http://127.0.0.1:8766"
        with self.assertRaisesRegex(W4AcceptanceError, "public"):
            validate_hosted_report(report)

        report = valid_hosted_report()
        report["deployed_version"] = ""
        with self.assertRaisesRegex(W4AcceptanceError, "deployed_version"):
            validate_hosted_report(report)

        report = valid_hosted_report()
        report["scenario"]["model_run"]["real_model"] = False
        with self.assertRaisesRegex(W4AcceptanceError, "real-model"):
            validate_hosted_report(report)

    def test_template_report_requires_exact_template_hash_all_fields_and_reopened_output(self):
        tmp, root, template = make_template_root()
        with tmp:
            report = valid_template_report(root, template)
            validate_template_report(report, root)

            changed = json.loads(json.dumps(report))
            changed["source_template"]["path"] = "docs/other.docx"
            with self.assertRaisesRegex(W4AcceptanceError, "source_template.path"):
                validate_template_report(changed, root)

            changed = json.loads(json.dumps(report))
            changed["source_template"]["sha256"] = "0" * 64
            with self.assertRaisesRegex(W4AcceptanceError, "sha256"):
                validate_template_report(changed, root)

            changed = json.loads(json.dumps(report))
            changed["fill"]["filled_fields"] = ["selected_framework"]
            with self.assertRaisesRegex(W4AcceptanceError, "filled_fields"):
                validate_template_report(changed, root)

    def test_model_eval_report_requires_committed_w4_eval_paths_and_real_model(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report = valid_model_eval_report(root)
            validate_model_eval_report(report, root)

            changed = json.loads(json.dumps(report))
            changed["workflow"] = "W3"
            with self.assertRaisesRegex(W4AcceptanceError, "workflow"):
                validate_model_eval_report(changed, root)

            changed = json.loads(json.dumps(report))
            changed["evidence"][2]["value"] = "eval-results/missing.txt"
            with self.assertRaisesRegex(W4AcceptanceError, "evidence"):
                validate_model_eval_report(changed, root)

            changed = json.loads(json.dumps(report))
            changed["model_run"]["real_model"] = False
            with self.assertRaisesRegex(W4AcceptanceError, "real-model"):
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
                with self.assertRaises(W4AcceptanceError):
                    validate_web_report(report)

        report = valid_web_report()
        report["nested"] = {"score": float("nan")}
        with self.assertRaisesRegex(W4AcceptanceError, "finite"):
            validate_web_report(report)

    def test_writer_is_stable_and_rejects_non_finite_numbers(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "nested" / "report.json"
            report = valid_web_report()
            write_sanitized_report(path, report)
            first = path.read_bytes()
            write_sanitized_report(path, report)
            self.assertEqual(first, path.read_bytes())

            with self.assertRaises(W4AcceptanceError):
                write_sanitized_report(Path(directory) / "bad.json", {"value": float("inf")})


if __name__ == "__main__":
    unittest.main()
