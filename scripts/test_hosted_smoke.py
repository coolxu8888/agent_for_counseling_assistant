import unittest
import json
from pathlib import Path
from unittest.mock import Mock

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

import hosted_smoke


class HostedSmokeTest(unittest.TestCase):
    def _w1_payload(self, mode):
        sections = {"basic_situation": {"known_facts": ["已提供去标识化线索"]}}
        return {
            "status": "success",
            "workflow": "W1",
            "detected_workflow": "W1",
            "route_status": "manual",
            "w1_mode": mode,
            "clean_output": "已生成去标识化结果",
            "structured_output": {"workflow": "W1", "sections": sections},
            "structured_check": {"status": "PASS"},
            "metadata": {"status": "success", "provider": "deepseek", "model": "configured-hosted-model"},
            "docx": {"status": "PASS", "path": "output.docx", "check": {"status": "PASS"}},
        }

    def test_run_w1_acceptance_aggregates_full_sanitized_evidence(self):
        responses = []
        for mode in ("intake_prep", "initial_interview_summary"):
            responses.extend(
                [
                    (200, {"status": "ok"}, {}),
                    (200, {"openapi": "https://host.example.com/openapi.json", "deployment_readiness": {"pilot_ready": True, "summary": {"fail_count": 0, "warn_count": 0}, "checks": []}}, {}),
                    (200, {"paths": {"/run_workflow": {}, "/draft_template": {}}}, {}),
                    (200, {"auth_config": {"signup_enabled": False, "invite_required": False}}, {}),
                    (200, {"status": "success"}, {"set-cookie": "session=private"}),
                    (200, self._w1_payload(mode), {}),
                ]
            )
        request_json = Mock(side_effect=responses)

        report = hosted_smoke.run_w1_acceptance(
            "https://host.example.com",
            username="operator",
            password="private-password",
            deployed_version="abc123",
            request_json=request_json,
        )

        self.assertEqual(report["report_type"], "hosted")
        self.assertEqual(report["deployed_version"], "abc123")
        self.assertEqual({item["mode"] for item in report["scenarios"]}, {"intake_prep", "initial_interview_summary"})
        for scenario in report["scenarios"]:
            self.assertEqual(scenario["http_status"], 200)
            self.assertEqual(scenario["workflow"], "W1")
            self.assertEqual(scenario["structured_result"]["status"], "PASS")
            self.assertTrue(scenario["model_run"]["real_model"])
            self.assertEqual(scenario["artifact"]["format"], "docx")
            self.assertEqual(scenario["artifact"]["download_assertion"], "passed")
        serialized = json.dumps(report, ensure_ascii=False)
        self.assertNotIn("private-password", serialized)
        self.assertNotIn("session=private", serialized)
        self.assertNotIn("run_dir", serialized)
        self.assertTrue(all(call.kwargs.get("payload", {}).get("render_docx") is True for call in request_json.call_args_list if call.args[1] == "/api/run"))

    def test_run_w1_acceptance_rejects_route_only_success(self):
        route_only = self._w1_payload("intake_prep")
        route_only["structured_check"] = None
        route_only["docx"] = {"status": "skipped", "path": None, "check": None}
        responses = [
            (200, {"status": "ok"}, {}),
            (200, {"openapi": "https://host.example.com/openapi.json", "deployment_readiness": {"pilot_ready": True, "summary": {}, "checks": []}}, {}),
            (200, {"paths": {"/run_workflow": {}, "/draft_template": {}}}, {}),
            (200, {"auth_config": {"signup_enabled": False}}, {}),
            (200, {"status": "success"}, {"set-cookie": "session=private"}),
            (200, route_only, {}),
        ]

        with self.assertRaisesRegex(ValueError, "structured validation.*PASS"):
            hosted_smoke.run_w1_acceptance(
                "https://host.example.com",
                username="operator",
                password="private-password",
                deployed_version="abc123",
                request_json=Mock(side_effect=responses),
            )

    def test_acceptance_rejects_real_run_annotation_without_model_metadata(self):
        smoke = {
            "workflow": {
                "http_status": 200, "workflow": "W1", "detected_workflow": "W1",
                "w1_mode": "intake_prep", "real_run": True,
                "structured_result": {"status": "PASS"},
                "structured_sections": {"basic_situation": {}},
                "artifact": {"status": "PASS", "path": "output.docx", "check": {"status": "PASS"}},
            }
        }
        with self.assertRaisesRegex(ValueError, "real model metadata"):
            hosted_smoke._acceptance_scenario("intake_prep", "去标识化场景", smoke)

    def test_w1_acceptance_cli_writes_report_only_after_validation(self):
        args = hosted_smoke.parse_args([
            "--base-url", "https://host.example.com", "--w1-acceptance",
            "--deployed-version", "abc123", "--report-output", "hosted.json",
        ])
        self.assertTrue(args.w1_acceptance)
        self.assertEqual(args.report_output, "hosted.json")

    def test_parse_args_accepts_w5_workflow_choice(self):
        args = hosted_smoke.parse_args(["--base-url", "https://example.test", "--workflow", "W5"])

        self.assertEqual(args.workflow, "W5")

    def test_parse_args_accepts_auto_workflow_choice(self):
        args = hosted_smoke.parse_args(["--base-url", "https://example.test", "--workflow", "AUTO"])

        self.assertEqual(args.workflow, "AUTO")

    def test_parse_args_accepts_route_metadata_expectations(self):
        args = hosted_smoke.parse_args(
            [
                "--base-url",
                "https://example.test",
                "--workflow",
                "AUTO",
                "--expect-route-status",
                "mixed_signals",
                "--expect-route-notice-substring",
                "case background",
            ]
        )

        self.assertEqual(args.expect_route_status, "mixed_signals")
        self.assertEqual(args.expect_route_notice_substring, "case background")

    def test_run_smoke_checks_core_endpoints_and_login(self):
        request_json = Mock(
            side_effect=[
                (200, {"status": "ok"}, {}),
                (
                    200,
                    {
                        "openapi": "https://example.test/openapi.json",
                        "deployment_readiness": {
                            "pilot_ready": True,
                            "summary": {"fail_count": 0, "warn_count": 1},
                            "checks": [],
                        },
                    },
                    {},
                ),
                (200, {"paths": {"/run_workflow": {}, "/draft_template": {}}}, {}),
                (
                    200,
                    {
                        "auth_config": {"signup_enabled": False, "invite_required": False},
                        "deployment_readiness": {
                            "pilot_ready": True,
                            "summary": {"fail_count": 0, "warn_count": 1},
                            "checks": [],
                        },
                    },
                    {},
                ),
                (200, {"status": "success", "user": {"username": "pilot"}}, {"set-cookie": "session=abc"}),
                (
                    200,
                    {
                        "status": "success",
                        "workflow": "W2",
                        "clean_output": "summary ready",
                        "structured_output": {"workflow": "W2"},
                    },
                    {},
                ),
            ]
        )

        report = hosted_smoke.run_smoke(
            "https://example.test",
            username="pilot",
            password="pilot-pass-123",
            real_run=True,
            request_json=request_json,
        )

        self.assertEqual(report["base_url"], "https://example.test")
        self.assertEqual(report["auth_mode"], "login")
        self.assertEqual(report["workflow"]["workflow"], "W2")
        self.assertEqual(report["workflow"]["output_excerpt"], "summary ready")
        self.assertEqual(request_json.call_args_list[4].args[1], "/api/login")
        self.assertEqual(request_json.call_args_list[5].args[1], "/api/run")

    def test_run_smoke_uses_signup_when_requested(self):
        request_json = Mock(
            side_effect=[
                (200, {"status": "ok"}, {}),
                (
                    200,
                    {
                        "openapi": "https://example.test/openapi.json",
                        "deployment_readiness": {
                            "pilot_ready": True,
                            "summary": {"fail_count": 0, "warn_count": 1},
                            "checks": [],
                        },
                    },
                    {},
                ),
                (200, {"paths": {"/run_workflow": {}, "/draft_template": {}}}, {}),
                (
                    200,
                    {
                        "auth_config": {"signup_enabled": True, "invite_required": True},
                        "deployment_readiness": {
                            "pilot_ready": True,
                            "summary": {"fail_count": 0, "warn_count": 1},
                            "checks": [],
                        },
                    },
                    {},
                ),
                (200, {"status": "success", "user": {"username": "pilot.new"}}, {"set-cookie": "session=abc"}),
            ]
        )

        report = hosted_smoke.run_smoke(
            "https://example.test",
            username="pilot.new",
            password="pilot-pass-123",
            invite_code="invite-123",
            require_signup=True,
            skip_run=True,
            request_json=request_json,
        )

        self.assertEqual(report["auth_mode"], "signup")
        self.assertEqual(request_json.call_args_list[4].args[1], "/api/signup")
        self.assertEqual(request_json.call_args_list[4].kwargs["payload"]["invite_code"], "invite-123")

    def test_run_smoke_requires_expected_auto_route_metadata(self):
        request_json = Mock(
            side_effect=[
                (200, {"status": "ok"}, {}),
                (
                    200,
                    {
                        "openapi": "https://example.test/openapi.json",
                        "deployment_readiness": {
                            "pilot_ready": True,
                            "summary": {"fail_count": 0, "warn_count": 1},
                            "checks": [],
                        },
                    },
                    {},
                ),
                (200, {"paths": {"/run_workflow": {}, "/draft_template": {}}}, {}),
                (
                    200,
                    {
                        "auth_config": {"signup_enabled": False, "invite_required": False},
                        "deployment_readiness": {
                            "pilot_ready": True,
                            "summary": {"fail_count": 0, "warn_count": 1},
                            "checks": [],
                        },
                    },
                    {},
                ),
                (200, {"status": "success", "user": {"username": "pilot"}}, {"set-cookie": "session=abc"}),
                (
                    200,
                    {
                        "status": "success",
                        "workflow": "W1",
                        "detected_workflow": "W1",
                        "route_status": "mixed_signals",
                        "route_notice": "Initial interview summary because the request asked for the fixed template instead of a counseling record.",
                        "w1_mode": "initial_interview_summary",
                        "routing_reasons_summary": "W1 via intake summary cues; W3 down-ranked by negated record wording.",
                        "w1_summary_brief": {"main_distress": "Sleep worsened after the breakup."},
                        "clean_output": "summary ready",
                        "structured_output": {"workflow": "W1"},
                    },
                    {},
                ),
            ]
        )

        report = hosted_smoke.run_smoke(
            "https://example.test",
            username="pilot",
            password="pilot-pass-123",
            workflow="AUTO",
            input_text="Please organize completed first-interview material with the fixed template rather than a counseling record.",
            expect_detected_workflow="W1",
            expect_route_status="mixed_signals",
            expect_route_notice_substring="fixed template",
            expect_w1_mode="initial_interview_summary",
            expect_route_summary_substring="W1 via intake summary cues",
            expect_w1_summary_brief=True,
            request_json=request_json,
        )

        self.assertEqual(report["workflow"]["workflow"], "W1")
        self.assertEqual(report["workflow"]["detected_workflow"], "W1")
        self.assertEqual(report["workflow"]["route_status"], "mixed_signals")
        self.assertEqual(report["workflow"]["w1_mode"], "initial_interview_summary")
        self.assertIn("fixed template", report["workflow"]["route_notice"])
        self.assertIn("W1 via intake summary cues", report["workflow"]["routing_reasons_summary"])

    def test_run_smoke_rejects_not_ready_deployment_when_required(self):
        request_json = Mock(
            side_effect=[
                (200, {"status": "ok"}, {}),
                (
                    200,
                    {
                        "openapi": "https://example.test/openapi.json",
                        "deployment_readiness": {
                            "pilot_ready": False,
                            "summary": {"fail_count": 1, "warn_count": 1},
                            "checks": [{"id": "deepseek_api", "status": "fail"}],
                        },
                    },
                    {},
                ),
            ]
        )

        with self.assertRaisesRegex(ValueError, "pilot_ready=false"):
            hosted_smoke.run_smoke(
                "https://example.test",
                expect_pilot_ready=True,
                skip_auth=True,
                skip_run=True,
                request_json=request_json,
            )


if __name__ == "__main__":
    unittest.main()
