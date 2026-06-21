import unittest
from pathlib import Path
from unittest.mock import Mock

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

import hosted_smoke


class HostedSmokeTest(unittest.TestCase):
    def test_parse_args_accepts_w5_workflow_choice(self):
        args = hosted_smoke.parse_args(["--base-url", "https://example.test", "--workflow", "W5"])

        self.assertEqual(args.workflow, "W5")

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
                        }
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
                        }
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
                        }
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
