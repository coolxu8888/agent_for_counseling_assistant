import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from w3_acceptance import (
    W3AcceptanceError,
    W3_REQUIRED_FIELDS,
    W3_TEMPLATE_PATH,
    W3_VISIBLE_LABEL,
    validate_hosted_report,
    validate_template_report,
    validate_web_report,
    write_sanitized_report,
)


def artifact():
    return {
        "format": "docx",
        "editable": True,
        "download_assertion": "passed",
        "filename": "w3-output.docx",
    }


def structured_result():
    return {
        "status": "PASS",
        "fields": {
            "record_format": "SOAP",
            "session_sections": {
                "subjective": ["Client reported panic decreased compared with last week."],
                "objective": ["Counselor observed steadier breathing after grounding practice."],
                "assessment": ["Distress appears reduced, while family conflict remains a trigger."],
                "plan": ["Practice grounding and review support options next session."],
            },
            "risk_change": {
                "current_status": ["Client denied current intent or plan in this de-identified note."],
                "change_since_last_contact": ["Panic intensity decreased from last week."],
                "follow_up_actions": ["Recheck ideation, intent, plan, means, and protective supports."],
            },
            "next_session_focus": ["Review grounding practice and family-boundary stressors."],
            "boundary_notes": ["This record documents provided material only and is not a diagnosis."],
        },
    }


def valid_web_report():
    return {
        "report_type": "web",
        "base_url": "http://127.0.0.1:8766",
        "timestamp_utc": "2026-07-10T08:00:00Z",
        "scenario": {
            "workflow": "W3",
            "visible_label": W3_VISIBLE_LABEL,
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
        sanitized_input="De-identified W3 SOAP counseling-record scenario.",
        model_run={"status": "success", "real_model": True, "provider": "deepseek", "model": "deepseek-chat"},
    )
    return report


def make_template_root():
    tmp = tempfile.TemporaryDirectory()
    root = Path(tmp.name)
    template = root / W3_TEMPLATE_PATH
    template.parent.mkdir(parents=True, exist_ok=True)
    template.write_bytes(b"fake docx identity for W3 acceptance contract")
    return tmp, root, template


def valid_template_report(root, template):
    return {
        "report_type": "template",
        "timestamp_utc": "2026-07-10T08:00:00Z",
        "workflow": "W3",
        "source_template": {
            "path": W3_TEMPLATE_PATH,
            "sha256": hashlib.sha256(template.read_bytes()).hexdigest(),
        },
        "fill": {"status": "PASS", "filled_fields": list(W3_REQUIRED_FIELDS), "unfilled_fields": [], "issues": []},
        "output_verification": {
            "status": "PASS",
            "reopened": True,
            "required_content": {field: f"verified W3 content for {field}" for field in W3_REQUIRED_FIELDS},
        },
    }


class W3AcceptanceTests(unittest.TestCase):
    def test_web_report_accepts_single_w3_counseling_record_scenario(self):
        validate_web_report(valid_web_report())

    def test_web_report_requires_w3_chinese_label_structured_record_and_docx(self):
        report = valid_web_report()
        report["scenario"]["workflow"] = "W2"
        with self.assertRaisesRegex(W3AcceptanceError, "workflow"):
            validate_web_report(report)

        report = valid_web_report()
        report["scenario"]["visible_label"] = "Session note"
        with self.assertRaisesRegex(W3AcceptanceError, "visible_label"):
            validate_web_report(report)

        report = valid_web_report()
        del report["scenario"]["structured_result"]["fields"]["session_sections"]["assessment"]
        with self.assertRaisesRegex(W3AcceptanceError, "session_sections.assessment"):
            validate_web_report(report)

        report = valid_web_report()
        report["scenario"]["structured_result"]["fields"]["record_format"] = "narrative"
        with self.assertRaisesRegex(W3AcceptanceError, "record_format"):
            validate_web_report(report)

        report = valid_web_report()
        report["scenario"]["artifact"]["editable"] = False
        with self.assertRaisesRegex(W3AcceptanceError, "editable"):
            validate_web_report(report)

    def test_hosted_report_requires_public_https_http_200_real_model_and_deployed_version(self):
        validate_hosted_report(valid_hosted_report())

        report = valid_hosted_report()
        report["base_url"] = "http://127.0.0.1:8766"
        with self.assertRaisesRegex(W3AcceptanceError, "public"):
            validate_hosted_report(report)

        report = valid_hosted_report()
        report["deployed_version"] = ""
        with self.assertRaisesRegex(W3AcceptanceError, "deployed_version"):
            validate_hosted_report(report)

        report = valid_hosted_report()
        report["scenario"]["model_run"]["real_model"] = False
        with self.assertRaisesRegex(W3AcceptanceError, "real-model"):
            validate_hosted_report(report)

        report = valid_hosted_report()
        report["scenario"]["http_status"] = 502
        with self.assertRaisesRegex(W3AcceptanceError, "HTTP 200"):
            validate_hosted_report(report)

    def test_template_report_requires_exact_template_hash_all_fields_and_reopened_output(self):
        tmp, root, template = make_template_root()
        with tmp:
            report = valid_template_report(root, template)
            validate_template_report(report, root)

            changed = json.loads(json.dumps(report))
            changed["source_template"]["path"] = "docs/other.docx"
            with self.assertRaisesRegex(W3AcceptanceError, "source_template.path"):
                validate_template_report(changed, root)

            changed = json.loads(json.dumps(report))
            changed["source_template"]["sha256"] = "0" * 64
            with self.assertRaisesRegex(W3AcceptanceError, "sha256"):
                validate_template_report(changed, root)

            changed = json.loads(json.dumps(report))
            changed["fill"]["filled_fields"] = ["record_format"]
            with self.assertRaisesRegex(W3AcceptanceError, "filled_fields"):
                validate_template_report(changed, root)

            changed = json.loads(json.dumps(report))
            changed["output_verification"]["required_content"]["risk_change"] = ""
            with self.assertRaisesRegex(W3AcceptanceError, "meaningful"):
                validate_template_report(changed, root)

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
                with self.assertRaises(W3AcceptanceError):
                    validate_web_report(report)

        report = valid_web_report()
        report["nested"] = {"score": float("nan")}
        with self.assertRaisesRegex(W3AcceptanceError, "finite"):
            validate_web_report(report)

    def test_writer_is_stable_and_rejects_non_finite_numbers(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "nested" / "report.json"
            report = valid_web_report()
            write_sanitized_report(path, report)
            first = path.read_bytes()
            write_sanitized_report(path, report)
            self.assertEqual(first, path.read_bytes())

            with self.assertRaises(W3AcceptanceError):
                write_sanitized_report(Path(directory) / "bad.json", {"value": float("inf")})


if __name__ == "__main__":
    unittest.main()
