import json
import hashlib
import tempfile
import unittest
from pathlib import Path

from w1_acceptance import (
    W1AcceptanceError,
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
        "filename": "w1-output.docx",
    }


def web_scenario(mode, label):
    return {
        "workflow": "W1",
        "mode": mode,
        "visible_label": label,
        "route_status": "passed",
        "structured_result": {"status": "PASS", "sections": ["目标", "内容"]},
        "artifact": artifact(),
    }


def valid_web_report():
    return {
        "report_type": "web",
        "base_url": "http://localhost:8000",
        "timestamp_utc": "2026-07-07T08:00:00Z",
        "scenarios": [
            web_scenario("intake_prep", "初始访谈准备"),
            web_scenario("initial_interview_summary", "初始访谈总结"),
        ],
    }


def valid_hosted_report():
    report = valid_web_report()
    report.update(
        report_type="hosted",
        base_url="https://example.invalid",
        deployed_version="abc1234",
    )
    for scenario in report["scenarios"]:
        scenario["model_run"] = {"status": "success", "real_model": True}
        scenario["sanitized_input"] = "去标识化场景"
    return report


class W1AcceptanceTests(unittest.TestCase):
    def test_w1_web_report_requires_both_modes(self):
        report = valid_web_report()
        validate_web_report(report)
        report["scenarios"].pop()
        with self.assertRaisesRegex(W1AcceptanceError, "both W1 modes"):
            validate_web_report(report)

    def test_w1_web_report_requires_chinese_visible_labels_and_full_assertions(self):
        for mutation in (
            lambda s: s.update(visible_label="Initial interview preparation"),
            lambda s: s.update(structured_result={"status": "PASS", "sections": []}),
            lambda s: s.update(artifact={"format": "docx", "editable": True}),
        ):
            report = valid_web_report()
            mutation(report["scenarios"][0])
            with self.subTest(report=report):
                with self.assertRaises(W1AcceptanceError):
                    validate_web_report(report)

    def test_w1_hosted_report_requires_model_and_artifact_assertions(self):
        validate_hosted_report(valid_hosted_report())
        mutations = (
            lambda r: r["scenarios"][0].pop("model_run"),
            lambda r: r["scenarios"][0]["model_run"].update(real_model=False),
            lambda r: r["scenarios"][0].update(route_status="passed"),
            lambda r: r["scenarios"][0]["artifact"].update(editable=False),
            lambda r: r.update(base_url="http://internal.example"),
        )
        for mutation in mutations:
            report = valid_hosted_report()
            mutation(report)
            if "model_run" in report["scenarios"][0] and mutation == mutations[2]:
                report["scenarios"][0].pop("structured_result")
            with self.subTest(report=report):
                with self.assertRaises(W1AcceptanceError):
                    validate_hosted_report(report)

    def test_template_report_requires_real_repo_template_and_reopened_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            template = root / "docs" / "初始访谈表.docx"
            template.parent.mkdir()
            template.write_bytes(b"real template fixture")
            report = {
                "report_type": "template",
                "timestamp_utc": "2026-07-07T08:00:00Z",
                "workflow": "W1",
                "mode": "initial_interview_summary",
                "source_template": {
                    "path": "docs/初始访谈表.docx",
                    "sha256": hashlib.sha256(template.read_bytes()).hexdigest(),
                },
                "fill": {"filled_fields": ["主诉", "初步评估"], "unfilled_fields": [], "issues": []},
                "output_verification": {
                    "status": "PASS",
                    "reopened": True,
                    "required_sections": {"主诉": True, "初步评估": True},
                },
            }
            validate_template_report(report, root)
            report["output_verification"]["reopened"] = False
            with self.assertRaises(W1AcceptanceError):
                validate_template_report(report, root)

    def test_report_rejects_secret_cookie_and_server_path_fields(self):
        unsafe_values = (
            ("api_token", "sk-live-secret"),
            ("api_key", "redacted-looking-but-forbidden"),
            ("cookies", "session=private"),
            ("notes", "Cookie: session=private"),
            ("output", "/srv/app/private/output.docx"),
            ("notes", "generated at /srv/app/private/output.docx"),
            ("output", r"C:\\Users\\server\\output.docx"),
        )
        for key, value in unsafe_values:
            report = valid_web_report()
            report[key] = value
            with self.subTest(key=key, value=value):
                with self.assertRaises(W1AcceptanceError):
                    validate_web_report(report)

    def test_write_report_is_stable_sanitized_json(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "nested" / "report.json"
            report = {"z": 1, "a": {"中": "文", "b": 2}}
            write_sanitized_report(path, report)
            first = path.read_bytes()
            write_sanitized_report(path, report)
            self.assertEqual(first, path.read_bytes())
            self.assertEqual(first, (json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8"))


if __name__ == "__main__":
    unittest.main()
