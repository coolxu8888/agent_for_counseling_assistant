import json
import hashlib
import tempfile
import unittest
from pathlib import Path

from w1_acceptance import (
    W1_SUMMARY_SECTIONS,
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
        base_url="https://app.render.com",
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

    def test_w1_web_report_requires_the_mode_specific_all_chinese_label(self):
        for mode, unsafe_label in (
            ("intake_prep", "初始访谈总结"),
            ("initial_interview_summary", "初始访谈准备"),
            ("intake_prep", "W1 初始访谈准备"),
            ("initial_interview_summary", "初始访谈 summary"),
        ):
            report = valid_web_report()
            next(item for item in report["scenarios"] if item["mode"] == mode)["visible_label"] = unsafe_label
            with self.subTest(mode=mode, label=unsafe_label):
                with self.assertRaisesRegex(W1AcceptanceError, "visible_label"):
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

    def test_w1_hosted_report_rejects_non_public_hosts_offline(self):
        for url in (
            "https://10.0.0.1",
            "https://127.0.0.1",
            "https://169.254.1.1",
            "https://192.0.2.1",
            "https://[::1]",
            "https://service",
            "https://service.local",
            "https://example.invalid",
            "https://user:password@app.render.com",
        ):
            report = valid_hosted_report()
            report["base_url"] = url
            with self.subTest(url=url):
                with self.assertRaisesRegex(W1AcceptanceError, "public"):
                    validate_hosted_report(report)

    def _valid_template_report(self):
        root = Path(__file__).resolve().parents[1]
        relative = Path("docs") / "4.心理咨询初始访谈表_20210906.docx"
        template = root / relative
        return root, {
            "report_type": "template",
            "timestamp_utc": "2026-07-07T08:00:00Z",
            "workflow": "W1",
            "mode": "initial_interview_summary",
            "source_template": {
                "path": relative.as_posix(),
                "sha256": hashlib.sha256(template.read_bytes()).hexdigest(),
            },
            "fill": {"filled_fields": list(W1_SUMMARY_SECTIONS), "unfilled_fields": [], "issues": []},
            "output_verification": {
                "status": "PASS",
                "reopened": True,
                "required_sections": {section: f"已映射内容：{section}" for section in W1_SUMMARY_SECTIONS},
            },
        }

    def test_template_report_requires_exact_real_repo_template_and_actual_hash(self):
        root, report = self._valid_template_report()
        validate_template_report(report, root)
        for mutation in (
            lambda r: r["source_template"].update(path="docs/another.docx"),
            lambda r: r["source_template"].update(sha256="0" * 64),
        ):
            changed = json.loads(json.dumps(report, ensure_ascii=False))
            mutation(changed)
            with self.assertRaises(W1AcceptanceError):
                validate_template_report(changed, root)

    def test_template_report_requires_reopened_canonical_sections_with_meaningful_coverage(self):
        root, report = self._valid_template_report()
        mutations = (
            lambda r: r["output_verification"].update(reopened=False),
            lambda r: r["output_verification"]["required_sections"].pop(W1_SUMMARY_SECTIONS[0]),
            lambda r: r["output_verification"]["required_sections"].update({W1_SUMMARY_SECTIONS[0]: ""}),
            lambda r: r["fill"].update(filled_fields=[W1_SUMMARY_SECTIONS[0]]),
        )
        for mutation in mutations:
            changed = json.loads(json.dumps(report, ensure_ascii=False))
            mutation(changed)
            with self.subTest(report=changed):
                with self.assertRaises(W1AcceptanceError):
                    validate_template_report(changed, root)

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

    def test_report_rejects_sensitive_assignments_inside_ordinary_strings(self):
        unsafe = (
            "password=hunter2",
            "access_token: abc123",
            "session_id = opaque-value",
            "cookie_name=private",
            "client_secret=private",
            "API key: private",
            "api_key=private",
            "credential: private",
            "credentials = private",
            "private key: private",
            "private_key=private",
            "前缀 password : private 后缀",
        )
        for value in unsafe:
            report = valid_web_report()
            report["notes"] = value
            with self.subTest(value=value):
                with self.assertRaises(W1AcceptanceError):
                    validate_web_report(report)

    def test_report_allows_non_assignment_uses_of_sensitive_words(self):
        report = valid_web_report()
        report["notes"] = [
            "password guidance",
            "token budget",
            "session summary",
            "cookie policy",
            "secret management guidance",
            "API key rotation guidance",
            "credential storage policy",
            "private key handling guidance",
        ]
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
