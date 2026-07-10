import unittest
import json
from pathlib import Path
from unittest.mock import Mock

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

import hosted_smoke
from run_agent import detect_w1_mode
from w2_acceptance import W2_VISIBLE_LABEL
from w3_acceptance import W3_VISIBLE_LABEL
from w4_acceptance import W4_VISIBLE_LABEL


class HostedSmokeTest(unittest.TestCase):
    def test_built_in_w1_scenarios_select_their_expected_modes(self):
        for expected_mode, scenario in hosted_smoke.W1_HOSTED_SCENARIOS.items():
            with self.subTest(mode=expected_mode):
                self.assertEqual(detect_w1_mode(scenario), expected_mode)

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

    def _w2_payload(self):
        return {
            "status": "success",
            "workflow": "W2",
            "detected_workflow": "W2",
            "route_status": "manual",
            "routing_reasons_summary": "W2 Case background",
            "clean_output": "已生成去标识化个案背景",
            "structured_output": {
                "workflow": "W2",
                "document_type": "case_summary",
                "presenting_concerns": ["Sleep disruption and family pressure."],
                "case_overview": {
                    "known_facts": ["Adult client with family and job stress."],
                    "working_hypotheses": ["Stress overload may maintain insomnia."],
                    "information_gaps": ["Support network details are unclear."],
                },
                "bio_psycho_social": {
                    "biological": {
                        "known_facts": ["Six months of insomnia."],
                        "working_hypotheses": ["Fatigue may intensify distress."],
                        "information_gaps": ["Appetite changes are unclear."],
                        "follow_up_questions": ["How many hours is the client sleeping?"],
                    },
                    "psychological": {
                        "known_facts": ["Job-performance anxiety is reported."],
                        "working_hypotheses": ["Self-criticism may amplify anxiety."],
                        "information_gaps": ["Automatic thoughts are unclear."],
                        "follow_up_questions": ["What thoughts follow work mistakes?"],
                    },
                    "social": {
                        "known_facts": ["Family pressure about marriage is active."],
                        "working_hypotheses": ["Reduced support may maintain distress."],
                        "information_gaps": ["Peer support is unclear."],
                        "follow_up_questions": ["Who can offer practical support?"],
                    },
                },
                "protective_factors": ["Help-seeking and work attendance."],
                "risk_formulation": {
                    "observed_clues": ["Heavy drinking alone after conflict."],
                    "missing_or_unclear": ["Escalation and means access are unclear."],
                    "follow_up_questions": ["Ask about ideation, intent, plan, means, and support."],
                },
                "recommended_focus": ["Clarify timeline, support network, and risk follow-up."],
                "boundary_notes": ["This is not a diagnosis or final risk rating."],
            },
            "structured_check": {"status": "PASS"},
            "metadata": {"status": "success", "provider": "deepseek", "model": "configured-hosted-model"},
            "docx": {"status": "PASS", "path": "output.docx", "check": {"status": "PASS"}},
        }

    def _w3_payload(self):
        return {
            "status": "success",
            "workflow": "W3",
            "detected_workflow": "W3",
            "route_status": "manual",
            "routing_reasons_summary": "W3 Session note",
            "clean_output": "已生成去标识化咨询记录。",
            "structured_output": {
                "workflow": "W3",
                "document_type": "session_note",
                "record_format": "SOAP",
                "sections": [
                    {"id": "subjective", "heading": "Subjective", "content": "Client reported panic decreased from last week."},
                    {"id": "objective", "heading": "Objective", "content": "Counselor reviewed grounding practice."},
                    {"id": "assessment", "heading": "Assessment", "content": "Distress appears reduced while work stress remains active."},
                    {"id": "plan", "heading": "Plan", "content": "Continue grounding practice and review supports next session."},
                ],
                "risk_change": {
                    "content": "Client denied current suicide plan or intent.",
                    "change_documentation": "Panic decreased compared with last week.",
                    "follow_up_actions": ["Recheck ideation, intent, plan, means, and supports."],
                },
                "next_session_focus": ["Review grounding, risk changes, and support resources."],
                "boundary_notes": ["This is not a diagnosis or final risk rating."],
            },
            "structured_check": {"status": "PASS"},
            "metadata": {"status": "success", "provider": "deepseek", "model": "configured-hosted-model"},
            "docx": {"status": "PASS", "path": "output.docx", "check": {"status": "PASS"}},
        }

    def _w4_payload(self):
        return {
            "status": "success",
            "workflow": "W4",
            "detected_workflow": "W4",
            "route_status": "manual",
            "routing_reasons_summary": "W4 case conceptualization",
            "clean_output": "已生成去标识化个案概念化。",
            "structured_output": {
                "workflow": "W4",
                "document_type": "case_conceptualization",
                "selected_framework": "CBT",
                "known_facts": ["Client becomes anxious before performance reviews."],
                "presenting_patterns": ["Criticism, anxiety, rumination, and avoidance cycle."],
                "predisposing_factors": ["History of frequent comparison to higher-performing cousins."],
                "precipitating_factors": ["Recent conflict with supervisor."],
                "maintaining_factors": ["Avoiding colleagues reduces short-term anxiety but maintains fear."],
                "protective_factors": ["Help-seeking and no reported suicide plan."],
                "risk_considerations": ["Continue checking ideation, intent, plan, means, and support."],
                "working_hypotheses": ["Performance evaluation may activate inadequacy beliefs."],
                "questions_to_verify": ["What evidence supports the predicted criticism?"],
                "boundary_notes": ["Working hypothesis only; not a diagnosis or treatment plan."],
            },
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

    def test_run_w2_acceptance_aggregates_full_sanitized_evidence(self):
        request_json = Mock(
            side_effect=[
                (200, {"status": "ok"}, {}),
                (200, {"openapi": "https://host.example.com/openapi.json", "deployment_readiness": {"pilot_ready": True, "summary": {"fail_count": 0, "warn_count": 0}, "checks": []}}, {}),
                (200, {"paths": {"/run_workflow": {}, "/draft_template": {}}}, {}),
                (200, {"auth_config": {"signup_enabled": False}}, {}),
                (200, {"status": "success"}, {"Set-Cookie": "session=private; HttpOnly"}),
                (200, self._w2_payload(), {}),
            ]
        )

        report = hosted_smoke.run_w2_acceptance(
            "https://host.example.com",
            username="operator",
            password="private-password",
            deployed_version="abc123",
            request_json=request_json,
        )

        self.assertEqual(report["report_type"], "hosted")
        self.assertEqual(report["deployed_version"], "abc123")
        self.assertEqual(report["scenario"]["workflow"], "W2")
        self.assertEqual(report["scenario"]["visible_label"], W2_VISIBLE_LABEL)
        self.assertEqual(report["scenario"]["structured_result"]["status"], "PASS")
        self.assertIn("bio_psycho_social", report["scenario"]["structured_result"]["fields"])
        self.assertIn("trusted friend", report["scenario"]["sanitized_input"])
        self.assertTrue(report["scenario"]["model_run"]["real_model"])
        self.assertEqual(report["scenario"]["artifact"]["download_assertion"], "passed")
        serialized = json.dumps(report, ensure_ascii=False)
        self.assertNotIn("private-password", serialized)
        self.assertNotIn("session=private", serialized)
        self.assertNotIn("run_dir", serialized)
        self.assertTrue(all(call.kwargs.get("payload", {}).get("render_docx") is True for call in request_json.call_args_list if call.args[1] == "/api/run"))

    def test_run_w2_acceptance_rejects_route_only_success(self):
        payload = self._w2_payload()
        payload["structured_check"] = None
        payload["docx"] = {"status": "skipped", "path": None, "check": None}
        responses = [
            (200, {"status": "ok"}, {}),
            (200, {"openapi": "https://host.example.com/openapi.json", "deployment_readiness": {"pilot_ready": True, "summary": {}, "checks": []}}, {}),
            (200, {"paths": {"/run_workflow": {}, "/draft_template": {}}}, {}),
            (200, {"auth_config": {"signup_enabled": False}}, {}),
            (200, {"status": "success"}, {"Set-Cookie": "session=private; HttpOnly"}),
            (200, payload, {}),
        ]

        with self.assertRaisesRegex(ValueError, "structured validation.*PASS"):
            hosted_smoke.run_w2_acceptance(
                "https://host.example.com",
                username="operator",
                password="private-password",
                deployed_version="abc123",
                request_json=Mock(side_effect=responses),
            )

    def test_w2_acceptance_cli_writes_report_only_after_validation(self):
        args = hosted_smoke.parse_args([
            "--base-url", "https://host.example.com", "--w2-acceptance",
            "--deployed-version", "abc123", "--report-output", "hosted.json",
        ])
        self.assertTrue(args.w2_acceptance)
        self.assertEqual(args.report_output, "hosted.json")

    def test_run_w3_acceptance_aggregates_full_sanitized_evidence(self):
        request_json = Mock(
            side_effect=[
                (200, {"status": "ok"}, {}),
                (200, {"openapi": "https://host.example.com/openapi.json", "deployment_readiness": {"pilot_ready": True, "summary": {"fail_count": 0, "warn_count": 0}, "checks": []}}, {}),
                (200, {"paths": {"/run_workflow": {}, "/draft_template": {}}}, {}),
                (200, {"auth_config": {"signup_enabled": False}}, {}),
                (200, {"status": "success"}, {"Set-Cookie": "session=private; HttpOnly"}),
                (200, self._w3_payload(), {}),
            ]
        )

        report = hosted_smoke.run_w3_acceptance(
            "https://host.example.com",
            username="operator",
            password="private-password",
            deployed_version="abc123",
            request_json=request_json,
        )

        self.assertEqual(report["report_type"], "hosted")
        self.assertEqual(report["deployed_version"], "abc123")
        self.assertEqual(report["scenario"]["workflow"], "W3")
        self.assertEqual(report["scenario"]["visible_label"], W3_VISIBLE_LABEL)
        self.assertEqual(report["scenario"]["structured_result"]["status"], "PASS")
        fields = report["scenario"]["structured_result"]["fields"]
        self.assertEqual(fields["record_format"], "SOAP")
        self.assertIn("session_sections", fields)
        self.assertIn("risk_change", fields)
        self.assertIn("next_session_focus", fields)
        self.assertIn("trusted friend", report["scenario"]["sanitized_input"])
        self.assertTrue(report["scenario"]["model_run"]["real_model"])
        self.assertEqual(report["scenario"]["artifact"]["download_assertion"], "passed")
        serialized = json.dumps(report, ensure_ascii=False)
        self.assertNotIn("private-password", serialized)
        self.assertNotIn("session=private", serialized)
        self.assertNotIn("run_dir", serialized)
        self.assertTrue(all(call.kwargs.get("payload", {}).get("render_docx") is True for call in request_json.call_args_list if call.args[1] == "/api/run"))

    def test_run_w3_acceptance_rejects_route_only_success(self):
        payload = self._w3_payload()
        payload["structured_check"] = None
        payload["docx"] = {"status": "skipped", "path": None, "check": None}
        responses = [
            (200, {"status": "ok"}, {}),
            (200, {"openapi": "https://host.example.com/openapi.json", "deployment_readiness": {"pilot_ready": True, "summary": {}, "checks": []}}, {}),
            (200, {"paths": {"/run_workflow": {}, "/draft_template": {}}}, {}),
            (200, {"auth_config": {"signup_enabled": False}}, {}),
            (200, {"status": "success"}, {"Set-Cookie": "session=private; HttpOnly"}),
            (200, payload, {}),
        ]

        with self.assertRaisesRegex(ValueError, "structured validation.*PASS"):
            hosted_smoke.run_w3_acceptance(
                "https://host.example.com",
                username="operator",
                password="private-password",
                deployed_version="abc123",
                request_json=Mock(side_effect=responses),
            )

    def test_w3_acceptance_cli_writes_report_only_after_validation(self):
        args = hosted_smoke.parse_args([
            "--base-url", "https://host.example.com", "--w3-acceptance",
            "--deployed-version", "abc123", "--report-output", "hosted.json",
        ])
        self.assertTrue(args.w3_acceptance)
        self.assertEqual(args.report_output, "hosted.json")

    def test_run_w4_acceptance_aggregates_full_sanitized_evidence(self):
        request_json = Mock(
            side_effect=[
                (200, {"status": "ok"}, {}),
                (200, {"openapi": "https://host.example.com/openapi.json", "deployment_readiness": {"pilot_ready": True, "summary": {"fail_count": 0, "warn_count": 0}, "checks": []}}, {}),
                (200, {"paths": {"/run_workflow": {}, "/draft_template": {}}}, {}),
                (200, {"auth_config": {"signup_enabled": False}}, {}),
                (200, {"status": "success"}, {"Set-Cookie": "session=private; HttpOnly"}),
                (200, self._w4_payload(), {}),
            ]
        )

        report = hosted_smoke.run_w4_acceptance(
            "https://host.example.com",
            username="operator",
            password="private-password",
            deployed_version="abc123",
            request_json=request_json,
        )

        self.assertEqual(report["report_type"], "hosted")
        self.assertEqual(report["deployed_version"], "abc123")
        self.assertEqual(report["scenario"]["workflow"], "W4")
        self.assertEqual(report["scenario"]["visible_label"], W4_VISIBLE_LABEL)
        self.assertEqual(report["scenario"]["structured_result"]["status"], "PASS")
        fields = report["scenario"]["structured_result"]["fields"]
        self.assertEqual(fields["selected_framework"], "CBT")
        self.assertIn("working_hypotheses", fields)
        self.assertIn("questions_to_verify", fields)
        self.assertIn("performance reviews", report["scenario"]["sanitized_input"])
        self.assertTrue(report["scenario"]["model_run"]["real_model"])
        self.assertEqual(report["scenario"]["artifact"]["download_assertion"], "passed")
        run_calls = [call for call in request_json.call_args_list if call.args[1] == "/api/run"]
        self.assertEqual(run_calls[0].kwargs["payload"]["workflow"], "W4")
        self.assertTrue(all(call.kwargs.get("payload", {}).get("render_docx") is True for call in run_calls))

    def test_run_w4_acceptance_rejects_route_only_success(self):
        payload = self._w4_payload()
        payload["structured_check"] = None
        payload["docx"] = {"status": "skipped", "path": None, "check": None}
        responses = [
            (200, {"status": "ok"}, {}),
            (200, {"openapi": "https://host.example.com/openapi.json", "deployment_readiness": {"pilot_ready": True, "summary": {}, "checks": []}}, {}),
            (200, {"paths": {"/run_workflow": {}, "/draft_template": {}}}, {}),
            (200, {"auth_config": {"signup_enabled": False}}, {}),
            (200, {"status": "success"}, {"Set-Cookie": "session=private; HttpOnly"}),
            (200, payload, {}),
        ]

        with self.assertRaisesRegex(ValueError, "structured validation.*PASS"):
            hosted_smoke.run_w4_acceptance(
                "https://host.example.com",
                username="operator",
                password="private-password",
                deployed_version="abc123",
                request_json=Mock(side_effect=responses),
            )

    def test_w4_acceptance_cli_writes_report_only_after_validation(self):
        args = hosted_smoke.parse_args([
            "--base-url", "https://host.example.com", "--w4-acceptance",
            "--deployed-version", "abc123", "--report-output", "hosted.json",
        ])
        self.assertTrue(args.w4_acceptance)
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
