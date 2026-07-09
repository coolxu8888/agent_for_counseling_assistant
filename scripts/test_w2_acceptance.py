import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from w2_acceptance import (
    W2AcceptanceError,
    W2_REQUIRED_FIELDS,
    W2_TEMPLATE_PATH,
    W2_VISIBLE_LABEL,
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
        "filename": "w2-output.docx",
    }


def structured_result():
    return {
        "status": "PASS",
        "fields": {
            "presenting_concerns": ["Sleep disruption and family pressure."],
            "case_overview": {
                "known_facts": ["Adult client with recent job and family stress."],
                "working_hypotheses": ["Stress overload may maintain sleep problems."],
                "information_gaps": ["Support availability is unclear."],
            },
            "bio_psycho_social": {
                "biological": {
                    "known_facts": ["Sleep disruption is reported."],
                    "working_hypotheses": ["Fatigue may intensify distress."],
                    "information_gaps": ["Appetite changes are unclear."],
                    "follow_up_questions": ["How many hours is the client sleeping?"],
                },
                "psychological": {
                    "known_facts": ["Anxiety about work performance is reported."],
                    "working_hypotheses": ["Self-criticism may amplify distress."],
                    "information_gaps": ["Automatic thoughts are unclear."],
                    "follow_up_questions": ["What thoughts follow family conflict?"],
                },
                "social": {
                    "known_facts": ["Family pressure is active."],
                    "working_hypotheses": ["Reduced support may maintain distress."],
                    "information_gaps": ["Peer support is unclear."],
                    "follow_up_questions": ["Who can offer practical support?"],
                },
            },
            "protective_factors": ["Help-seeking and work attendance."],
            "risk_formulation": {
                "observed_clues": ["Heavy drinking after conflict was reported."],
                "missing_or_unclear": ["Means access and escalation are unclear."],
                "follow_up_questions": ["Ask about ideation, intent, plan, means, and support."],
            },
            "recommended_focus": ["Clarify timeline, support network, and risk follow-up."],
            "boundary_notes": ["This is not a diagnosis or final risk rating."],
        },
    }


def valid_web_report():
    return {
        "report_type": "web",
        "base_url": "http://127.0.0.1:8766",
        "timestamp_utc": "2026-07-09T08:00:00Z",
        "scenario": {
            "workflow": "W2",
            "visible_label": W2_VISIBLE_LABEL,
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
        sanitized_input="De-identified W2 BPS case background scenario.",
        model_run={"status": "success", "real_model": True, "provider": "deepseek", "model": "deepseek-chat"},
    )
    return report


def make_template_root():
    tmp = tempfile.TemporaryDirectory()
    root = Path(tmp.name)
    template = root / W2_TEMPLATE_PATH
    template.parent.mkdir(parents=True, exist_ok=True)
    template.write_bytes(b"fake docx identity for W2 acceptance contract")
    return tmp, root, template


def valid_template_report(root, template):
    return {
        "report_type": "template",
        "timestamp_utc": "2026-07-09T08:00:00Z",
        "workflow": "W2",
        "source_template": {
            "path": W2_TEMPLATE_PATH,
            "sha256": hashlib.sha256(template.read_bytes()).hexdigest(),
        },
        "fill": {"status": "PASS", "filled_fields": list(W2_REQUIRED_FIELDS), "unfilled_fields": [], "issues": []},
        "output_verification": {
            "status": "PASS",
            "reopened": True,
            "required_content": {field: f"verified W2 content for {field}" for field in W2_REQUIRED_FIELDS},
        },
    }


class W2AcceptanceTests(unittest.TestCase):
    def test_web_report_accepts_single_w2_bps_scenario(self):
        validate_web_report(valid_web_report())

    def test_web_report_requires_w2_chinese_label_structured_bps_and_docx(self):
        report = valid_web_report()
        report["scenario"]["workflow"] = "W1"
        with self.assertRaisesRegex(W2AcceptanceError, "workflow"):
            validate_web_report(report)

        report = valid_web_report()
        report["scenario"]["visible_label"] = "Case background"
        with self.assertRaisesRegex(W2AcceptanceError, "visible_label"):
            validate_web_report(report)

        report = valid_web_report()
        del report["scenario"]["structured_result"]["fields"]["bio_psycho_social"]["social"]
        with self.assertRaisesRegex(W2AcceptanceError, "bio_psycho_social.social"):
            validate_web_report(report)

        report = valid_web_report()
        report["scenario"]["artifact"]["editable"] = False
        with self.assertRaisesRegex(W2AcceptanceError, "editable"):
            validate_web_report(report)

    def test_hosted_report_requires_public_https_http_200_real_model_and_deployed_version(self):
        validate_hosted_report(valid_hosted_report())

        report = valid_hosted_report()
        report["base_url"] = "http://127.0.0.1:8766"
        with self.assertRaisesRegex(W2AcceptanceError, "public"):
            validate_hosted_report(report)

        report = valid_hosted_report()
        report["deployed_version"] = ""
        with self.assertRaisesRegex(W2AcceptanceError, "deployed_version"):
            validate_hosted_report(report)

        report = valid_hosted_report()
        report["scenario"]["model_run"]["real_model"] = False
        with self.assertRaisesRegex(W2AcceptanceError, "real-model"):
            validate_hosted_report(report)

        report = valid_hosted_report()
        report["scenario"]["http_status"] = 502
        with self.assertRaisesRegex(W2AcceptanceError, "HTTP 200"):
            validate_hosted_report(report)

    def test_template_report_requires_exact_template_hash_all_fields_and_reopened_output(self):
        tmp, root, template = make_template_root()
        with tmp:
            report = valid_template_report(root, template)
            validate_template_report(report, root)

            changed = json.loads(json.dumps(report))
            changed["source_template"]["path"] = "docs/other.docx"
            with self.assertRaisesRegex(W2AcceptanceError, "source_template.path"):
                validate_template_report(changed, root)

            changed = json.loads(json.dumps(report))
            changed["source_template"]["sha256"] = "0" * 64
            with self.assertRaisesRegex(W2AcceptanceError, "sha256"):
                validate_template_report(changed, root)

            changed = json.loads(json.dumps(report))
            changed["fill"]["filled_fields"] = ["presenting_concerns"]
            with self.assertRaisesRegex(W2AcceptanceError, "filled_fields"):
                validate_template_report(changed, root)

            changed = json.loads(json.dumps(report))
            changed["output_verification"]["required_content"]["risk_formulation"] = ""
            with self.assertRaisesRegex(W2AcceptanceError, "meaningful"):
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
                with self.assertRaises(W2AcceptanceError):
                    validate_web_report(report)

        report = valid_web_report()
        report["nested"] = {"score": float("nan")}
        with self.assertRaisesRegex(W2AcceptanceError, "finite"):
            validate_web_report(report)

    def test_writer_is_stable_and_rejects_non_finite_numbers(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "nested" / "report.json"
            report = valid_web_report()
            write_sanitized_report(path, report)
            first = path.read_bytes()
            write_sanitized_report(path, report)
            self.assertEqual(first, path.read_bytes())

            with self.assertRaises(W2AcceptanceError):
                write_sanitized_report(Path(directory) / "bad.json", {"value": float("inf")})


if __name__ == "__main__":
    unittest.main()
