import json
import sys
import tempfile
import unittest
import zipfile
import base64
from datetime import timedelta
from pathlib import Path
from urllib.parse import quote
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))

import web_workbench
from workbench_store import WorkbenchStore
from workbench_store import utc_now


WORD_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def write_test_docx(path, document_xml):
    with zipfile.ZipFile(path, "w") as package:
        package.writestr("[Content_Types].xml", "")
        package.writestr("word/document.xml", document_xml)


class FakeHandler:
    def __init__(self, headers=None):
        self.headers = headers or {}


class WebWorkbenchTest(unittest.TestCase):
    def test_json_response_encodes_utf8_payload(self):
        status, headers, body = web_workbench.json_response({"message": "咨询师助理"})

        self.assertEqual(status, 200)
        self.assertEqual(headers["Content-Type"], "application/json; charset=utf-8")
        self.assertEqual(json.loads(body.decode("utf-8")), {"message": "咨询师助理"})

    def test_error_response_uses_error_shape(self):
        status, headers, body = web_workbench.error_response(400, "Missing input")

        self.assertEqual(status, 400)
        self.assertEqual(headers["Content-Type"], "application/json; charset=utf-8")
        self.assertEqual(
            json.loads(body.decode("utf-8")),
            {"status": "error", "message": "Missing input"},
        )

    def test_static_file_path_resolves_inside_web_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            web_root = Path(tmp) / "web-workbench"
            web_root.mkdir()
            index_path = web_root / "index.html"
            index_path.write_text("<h1>ok</h1>", encoding="utf-8")

            resolved = web_workbench.resolve_static_path("/", web_root)

        self.assertEqual(resolved.name, "index.html")

    def test_static_index_has_valid_title_markup(self):
        index_path = web_workbench.resolve_static_path("/")
        html = index_path.read_text(encoding="utf-8")

        self.assertIn("<title>Counselor Assistant</title>", html)
        self.assertNotIn("?/title>", html)
        self.assertIn("&lt;&lt;</button>", html)
        self.assertIn('id="intentSummary"', html)
        self.assertIn('id="localeZhButton"', html)
        self.assertIn("咨询师工作台登录", html)
        self.assertIn("demo / demo123", html)

    def test_resolve_download_path_allows_agent_runs_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_root = root / "agent-runs"
            run_root.mkdir()
            output = run_root / "file.docx"
            output.write_bytes(b"docx")

            resolved = web_workbench.resolve_download_path(str(output), allowed_roots=[run_root])

        self.assertEqual(resolved.name, "file.docx")

    def test_resolve_download_path_rejects_outside_agent_runs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_root = root / "agent-runs"
            run_root.mkdir()
            outside = root / "secret.txt"
            outside.write_text("secret", encoding="utf-8")

            with self.assertRaises(ValueError):
                web_workbench.resolve_download_path(str(outside), allowed_roots=[run_root])

    def test_safe_content_disposition_includes_unicode_filename_star(self):
        header = web_workbench.safe_content_disposition("报告.docx")

        self.assertIn('filename="__.docx"', header)
        self.assertIn("filename*=UTF-8''%E6%8A%A5%E5%91%8A.docx", header)
        header.encode("ascii")

    def test_safe_content_disposition_sanitizes_unsafe_fallback_characters(self):
        header = web_workbench.safe_content_disposition('bad";\r\nname.docx')
        fallback = header.split("filename=", 1)[1].split(";", 1)[0]

        self.assertNotIn('"', fallback.strip('"'))
        self.assertNotIn(";", fallback)
        self.assertNotIn("\r", fallback)
        self.assertNotIn("\n", fallback)
        header.encode("ascii")

    def test_resolve_template_path_accepts_demo_template_ref(self):
        with tempfile.TemporaryDirectory() as tmp:
            docs_root = Path(tmp) / "docs"
            docs_root.mkdir()
            template = docs_root / "demo-template.docx"
            template.write_bytes(b"docx")

            with patch.object(web_workbench, "DOCS_ROOT", docs_root):
                resolved = web_workbench.resolve_template_path(
                    None,
                    template_ref="demo:demo-template",
                    user_id=7,
                )

        self.assertEqual(resolved, template.resolve())

    def test_resolve_template_path_accepts_owner_upload_template_ref(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = WorkbenchStore(Path(tmp) / "workbench.sqlite3", Path(tmp) / "uploads")
            auth = store.authenticate("demo", "demo123")
            upload = store.store_upload(
                auth["user"]["id"],
                "template.docx",
                "ZG9jeA==",
                content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )

            with patch.object(web_workbench, "STORE", store):
                resolved = web_workbench.resolve_template_path(
                    None,
                    template_ref=f"upload:{upload['id']}",
                    user_id=auth["user"]["id"],
                )

        self.assertEqual(resolved, Path(upload["stored_path"]).resolve())

    def test_resolve_template_path_rejects_other_users_upload_template_ref(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = WorkbenchStore(Path(tmp) / "workbench.sqlite3", Path(tmp) / "uploads")
            owner = store.authenticate("demo", "demo123")
            upload = store.store_upload(
                owner["user"]["id"],
                "template.docx",
                "ZG9jeA==",
                content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )

            with patch.object(web_workbench, "STORE", store):
                with self.assertRaises(PermissionError):
                    web_workbench.resolve_template_path(
                        None,
                        template_ref=f"upload:{upload['id']}",
                        user_id=owner["user"]["id"] + 1,
                    )

    def test_handle_file_download_uses_filename_star_for_unicode_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_root = root / "agent-runs"
            run_root.mkdir()
            output = run_root / "报告.docx"
            output.write_bytes(b"docx")
            request_path = "/files/" + quote(str(output), safe="")

            with patch.object(web_workbench, "RUN_ROOT", run_root):
                status, headers, body = web_workbench.handle_file_download(request_path)

        self.assertEqual(status, 200)
        self.assertEqual(body, b"docx")
        self.assertIn("filename*", headers["Content-Disposition"])
        self.assertIn("%E6%8A%A5%E5%91%8A.docx", headers["Content-Disposition"])
        headers["Content-Disposition"].encode("ascii")

    def test_handle_file_download_rejects_unregistered_run_artifact(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_root = root / "agent-runs"
            run_root.mkdir()
            output = run_root / "output.docx"
            output.write_bytes(b"docx")
            request_path = "/files/" + quote(str(output), safe="")
            user = {"id": 7, "username": "demo", "role": "counselor"}
            store = WorkbenchStore(Path(tmp) / "workbench.sqlite3", Path(tmp) / "uploads")

            with patch.object(web_workbench, "RUN_ROOT", run_root):
                with patch.object(web_workbench, "STORE", store):
                    status, _headers, body = web_workbench.handle_file_download(request_path, user=user)

        payload = json.loads(body.decode("utf-8"))
        self.assertEqual(status, 403)
        self.assertIn("not available", payload["message"])

    def test_handle_file_download_allows_registered_run_artifact_for_owner(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_root = root / "agent-runs"
            run_root.mkdir()
            output = run_root / "output.docx"
            output.write_bytes(b"docx")
            request_path = "/files/" + quote(str(output), safe="")
            store = WorkbenchStore(Path(tmp) / "workbench.sqlite3", Path(tmp) / "uploads")
            auth = store.authenticate("demo", "demo123")
            user = auth["user"]
            store.register_run_artifact(user["id"], str(run_root), workflow="W3")

            with patch.object(web_workbench, "RUN_ROOT", run_root):
                with patch.object(web_workbench, "STORE", store):
                    status, headers, body = web_workbench.handle_file_download(request_path, user=user)

        self.assertEqual(status, 200)
        self.assertEqual(body, b"docx")
        self.assertIn("attachment;", headers["Content-Disposition"])

    def test_handle_run_rejects_empty_input(self):
        response = web_workbench.handle_api_run({"workflow": "W1", "input": "   "})

        status, _headers, body = response
        self.assertEqual(status, 400)
        self.assertIn("Input is required", json.loads(body.decode("utf-8"))["message"])

    def test_detect_workflow_routes_intake_session_and_case_summary(self):
        self.assertEqual(web_workbench.detect_workflow("Create an intake information guide"), "W1")
        self.assertEqual(web_workbench.detect_workflow("Write a session note with next-session focus"), "W3")
        self.assertEqual(web_workbench.detect_workflow("Summarize this case using a BPS structure"), "W2")
        self.assertEqual(web_workbench.detect_workflow("Create a CBT case conceptualization hypothesis"), "W4")
        self.assertEqual(web_workbench.detect_workflow("Plan the next session agenda for this de-identified case"), "W5")
        self.assertEqual(web_workbench.detect_workflow("Create a phased counseling roadmap for this de-identified case"), "W6")

    def test_detect_workflow_routes_english_product_prompts(self):
        self.assertEqual(web_workbench.detect_workflow("Create an intake guide for a first session"), "W1")
        self.assertEqual(web_workbench.detect_workflow("Please draft a de-identified case summary for supervision"), "W2")
        self.assertEqual(web_workbench.detect_workflow("Write a session note and risk update"), "W3")
        self.assertEqual(web_workbench.detect_workflow("Use a psychodynamic framework to conceptualize this case"), "W4")
        self.assertEqual(web_workbench.detect_workflow("Create a CBT next-session plan with risk check points"), "W5")
        self.assertEqual(web_workbench.detect_workflow("Build an integrative multi-session counseling roadmap with phases"), "W6")

    def test_detect_workflow_routes_bps_case_background_requests_to_w2(self):
        self.assertEqual(
            web_workbench.detect_workflow(
                "Organize these notes into a biopsychosocial case background with presenting concerns, protective factors, and risk follow-up questions."
            ),
            "W2",
        )

    def test_detect_workflow_prefers_w1_for_pre_interview_preparation_requests(self):
        self.assertEqual(
            web_workbench.detect_workflow(
                "Before the first interview tomorrow, create an intake question guide and checklist for what I still need to ask."
            ),
            "W1",
        )

    def test_detect_workflow_prefers_w3_for_post_session_note_requests(self):
        self.assertEqual(
            web_workbench.detect_workflow(
                "These are my first interview notes from today. Turn them into a counseling record with a risk update and next session focus."
            ),
            "W3",
        )

    def test_detect_workflow_prefers_w1_for_initial_interview_summary_template_requests(self):
        self.assertEqual(
            web_workbench.detect_workflow(
                "These are completed initial interview notes, not a session record. Organize them into the fixed initial interview summary template."
            ),
            "W1",
        )

    def test_detect_workflow_prefers_w6_for_multi_session_planning_even_with_next_session_language(self):
        self.assertEqual(
            web_workbench.detect_workflow(
                "Map the next several sessions into a phased counseling roadmap, including the immediate next session and later phases."
            ),
            "W6",
        )

    def test_detect_workflow_prefers_w5_for_single_next_session_requests_even_with_framework_language(self):
        self.assertEqual(
            web_workbench.detect_workflow(
                "Using CBT, plan only the next counseling session agenda from this case conceptualization."
            ),
            "W5",
        )

    def test_detect_workflow_details_marks_mixed_signal_when_roadmap_request_mentions_next_session(self):
        details = web_workbench.detect_workflow_details(
            "Map the next several sessions into a phased counseling roadmap, including the immediate next session and later phases."
        )

        self.assertEqual(details["workflow"], "W6")
        self.assertEqual(details["route_status"], "mixed_signals")
        self.assertIn("roadmap", details["route_notice"].lower())
        self.assertEqual(details["top_candidates"][0]["workflow"], "W6")
        self.assertEqual(details["top_candidates"][1]["workflow"], "W5")

    def test_detect_workflow_details_marks_mixed_signal_when_initial_interview_summary_mentions_notes(self):
        details = web_workbench.detect_workflow_details(
            "These are completed initial interview notes, not a session record. Organize them into the fixed initial interview summary template."
        )

        self.assertEqual(details["workflow"], "W1")
        self.assertEqual(details["w1_mode"], "initial_interview_summary")
        self.assertEqual(details["route_status"], "mixed_signals")
        self.assertIn("fixed intake summary/template", details["route_notice"].lower())

    def test_detect_workflow_prefers_w1_for_bilingual_initial_interview_summary_prompt(self):
        details = web_workbench.detect_workflow_details(
            "请把 first interview notes 整理成固定初访总结模板，不要写成 session note。"
        )

        self.assertEqual(details["workflow"], "W1")
        self.assertEqual(details["w1_mode"], "initial_interview_summary")
        self.assertEqual(details["route_status"], "mixed_signals")
        self.assertEqual(details["top_candidates"][0]["workflow"], "W1")
        self.assertEqual(details["top_candidates"][1]["workflow"], "W3")

    def test_detect_workflow_prefers_w1_for_chinese_first_summary_prompt_that_negates_birp(self):
        details = web_workbench.detect_workflow_details(
            "请根据首访原始记录整理固定模板总结，保留风险变化线索，不要写成BIRP或咨询记录。"
        )

        self.assertEqual(details["workflow"], "W1")
        self.assertEqual(details["w1_mode"], "initial_interview_summary")
        self.assertEqual(details["route_status"], "mixed_signals")
        self.assertEqual(details["top_candidates"][0]["workflow"], "W1")
        self.assertEqual(details["top_candidates"][1]["workflow"], "W3")

    def test_detect_workflow_prefers_w1_for_chinese_first_summary_prompt_that_negates_soap(self):
        details = web_workbench.detect_workflow_details(
            "请根据首访原始记录整理固定模板总结，保留风险变化线索，不要写成SOAP或session note。"
        )

        self.assertEqual(details["workflow"], "W1")
        self.assertEqual(details["w1_mode"], "initial_interview_summary")
        self.assertEqual(details["route_status"], "mixed_signals")
        self.assertEqual(details["top_candidates"][0]["workflow"], "W1")
        self.assertEqual(details["top_candidates"][1]["workflow"], "W3")

    def test_detect_workflow_prefers_w1_for_loose_chinese_first_summary_prompt_that_negates_soap(self):
        details = web_workbench.detect_workflow_details(
            "请用固定模板整理首访材料，保留风险变化线索，不要写成SOAP。"
        )

        self.assertEqual(details["workflow"], "W1")
        self.assertEqual(details["w1_mode"], "initial_interview_summary")
        self.assertEqual(details["route_status"], "mixed_signals")
        self.assertEqual(details["top_candidates"][0]["workflow"], "W1")
        self.assertEqual(details["top_candidates"][1]["workflow"], "W3")

    def test_detect_workflow_prefers_w1_for_loose_fixed_template_summary_prompt_that_negates_record(self):
        details = web_workbench.detect_workflow_details(
            "请按固定模板梳理这次第一次访谈材料，保留风险变化线索，先不要做咨询记录。"
        )

        self.assertEqual(details["workflow"], "W1")
        self.assertEqual(details["w1_mode"], "initial_interview_summary")
        self.assertEqual(details["route_status"], "mixed_signals")
        self.assertEqual(details["top_candidates"][0]["workflow"], "W1")
        self.assertEqual(details["top_candidates"][1]["workflow"], "W3")

    def test_detect_workflow_prefers_w5_for_bilingual_single_session_plan_prompt(self):
        details = web_workbench.detect_workflow_details(
            "用 CBT 做下次咨询计划，只规划 next session，不要做多阶段 roadmap。"
        )

        self.assertEqual(details["workflow"], "W5")
        self.assertEqual(details["route_status"], "mixed_signals")
        self.assertEqual(details["top_candidates"][0]["workflow"], "W5")
        self.assertEqual(details["top_candidates"][1]["workflow"], "W6")

    def test_detect_workflow_prefers_w5_when_prompt_rejects_multi_session_roadmap_scope(self):
        details = web_workbench.detect_workflow_details(
            "Use a humanistic lens for this case. Plan only the next counseling session, include risk check points, "
            "and do not expand into a multi-session roadmap or later phases."
        )

        self.assertEqual(details["workflow"], "W5")
        self.assertEqual(details["route_status"], "mixed_signals")
        self.assertEqual(details["top_candidates"][0]["workflow"], "W5")
        self.assertEqual(details["top_candidates"][1]["workflow"], "W6")
        self.assertIn("next-session", details["route_notice"].lower())

    def test_detect_workflow_prefers_w4_for_conceptualization_request_that_negates_counseling_record(self):
        details = web_workbench.detect_workflow_details(
            "Use today's session notes to build a CBT case conceptualization with working hypotheses, not a counseling record."
        )

        self.assertEqual(details["workflow"], "W4")
        self.assertEqual(details["route_status"], "mixed_signals")
        self.assertEqual(details["top_candidates"][0]["workflow"], "W4")
        self.assertEqual(details["top_candidates"][1]["workflow"], "W3")
        self.assertIn("conceptualization", details["route_notice"].lower())

    def test_detect_workflow_prefers_w4_for_bilingual_conceptualization_request_that_negates_record(self):
        details = web_workbench.detect_workflow_details(
            "请根据今天session note整理CBT概念化，保留working hypotheses，不要写成咨询记录。"
        )

        self.assertEqual(details["workflow"], "W4")
        self.assertEqual(details["route_status"], "mixed_signals")
        self.assertEqual(details["top_candidates"][0]["workflow"], "W4")
        self.assertEqual(details["top_candidates"][1]["workflow"], "W3")
        self.assertIn("conceptualization", details["route_notice"].lower())

    def test_detect_workflow_prefers_w5_when_bilingual_next_session_request_negates_session_note(self):
        details = web_workbench.detect_workflow_details(
            "\u8bf7\u7528CBT\u505a\u4e0b\u6b21\u54a8\u8be2\u8ba1\u5212\uff0c"
            "\u53ea\u89c4\u5212next session\uff0c"
            "\u4e0d\u8981\u5199\u6210session note\u6216counseling record\u3002"
        )

        self.assertEqual(details["workflow"], "W5")
        self.assertEqual(details["route_status"], "mixed_signals")
        self.assertEqual(details["top_candidates"][0]["workflow"], "W5")
        self.assertEqual(details["top_candidates"][1]["workflow"], "W3")

    def test_detect_workflow_prefers_w5_when_bilingual_request_says_not_a_record(self):
        details = web_workbench.detect_workflow_details(
            "\u8fd9\u4e0d\u662f\u8981\u4f60\u5199session note\u6216\u54a8\u8be2\u8bb0\u5f55\uff0c"
            "\u53ea\u505a\u4e0b\u4e00\u6b21\u54a8\u8be2\u8ba1\u5212\u3002"
            "Use a humanistic lens and include risk check points."
        )

        self.assertEqual(details["workflow"], "W5")
        self.assertEqual(details["route_status"], "mixed_signals")
        self.assertEqual(details["top_candidates"][0]["workflow"], "W5")
        self.assertEqual(details["top_candidates"][1]["workflow"], "W3")
        self.assertIn("next-session", details["route_notice"].lower())

    def test_detect_workflow_prefers_w5_when_english_prompt_says_rather_than_record(self):
        details = web_workbench.detect_workflow_details(
            "Using a humanistic lens, create the next session agenda rather than a counseling record. "
            "Keep it to one upcoming counseling session and include risk check points."
        )

        self.assertEqual(details["workflow"], "W5")
        self.assertEqual(details["route_status"], "mixed_signals")
        self.assertEqual(details["top_candidates"][0]["workflow"], "W5")
        self.assertEqual(details["top_candidates"][1]["workflow"], "W3")

    def test_detect_workflow_prefers_w5_when_session_notes_are_only_source_material_for_next_session_agenda(self):
        details = web_workbench.detect_workflow_details(
            "Please use today's session notes to prepare the next session agenda rather than a counseling record, "
            "keep it to one upcoming counseling session, and include risk check points."
        )

        self.assertEqual(details["workflow"], "W5")
        self.assertEqual(details["route_status"], "mixed_signals")
        self.assertEqual(details["top_candidates"][0]["workflow"], "W5")
        self.assertEqual(details["top_candidates"][1]["workflow"], "W3")
        self.assertIn("next-session", details["route_notice"].lower())

    def test_detect_workflow_prefers_w5_for_chinese_session_note_source_material_prompt(self):
        details = web_workbench.detect_workflow_details(
            "请用今天的会谈记录作为素材，整理下一次咨询计划，保留风险检查点，不要写成咨询记录，只聚焦下一次会谈。"
        )

        self.assertEqual(details["workflow"], "W5")
        self.assertEqual(details["route_status"], "mixed_signals")
        self.assertEqual(details["top_candidates"][0]["workflow"], "W5")
        self.assertEqual(details["top_candidates"][1]["workflow"], "W3")
        self.assertIn("W5", details["routing_reasons_summary"])

    def test_detect_workflow_prefers_w2_when_case_background_request_negates_record_format(self):
        details = web_workbench.detect_workflow_details(
            "Please turn today's session note into a BPS case background for supervision, "
            "not a counseling record. Separate known facts, working hypotheses, protective factors, "
            "and risk follow-up questions."
        )

        self.assertEqual(details["workflow"], "W2")
        self.assertEqual(details["route_status"], "mixed_signals")
        self.assertEqual(details["top_candidates"][0]["workflow"], "W2")
        self.assertEqual(details["top_candidates"][1]["workflow"], "W3")

    def test_detect_workflow_prefers_w2_for_bilingual_case_background_request_that_negates_conceptualization(self):
        details = web_workbench.detect_workflow_details(
            "Use CBT to organize today's session note into a supervision case background, "
            "keep working hypotheses visible, and do not turn it into a case conceptualization."
        )

        self.assertEqual(details["workflow"], "W2")
        self.assertEqual(details["route_status"], "mixed_signals")
        self.assertEqual(details["top_candidates"][0]["workflow"], "W2")
        self.assertEqual(details["top_candidates"][1]["workflow"], "W4")
        self.assertIn("case background", details["route_notice"].lower())

    def test_detect_workflow_prefers_w2_for_completed_initial_interview_material_that_negates_w1_template_scope(self):
        details = web_workbench.detect_workflow_details(
            "These are completed first interview notes. Organize them into a BPS case background for supervision, "
            "keep known facts, working hypotheses, protective factors, and risk follow-up questions visible, "
            "and do not keep the fixed initial interview summary template."
        )

        self.assertEqual(details["workflow"], "W2")
        self.assertEqual(details["route_status"], "mixed_signals")
        self.assertEqual(details["top_candidates"][0]["workflow"], "W2")
        self.assertEqual(details["top_candidates"][1]["workflow"], "W1")
        self.assertIn("case background", details["route_notice"].lower())

    def test_detect_workflow_prefers_w2_for_chinese_intake_material_background_request_that_negates_w1_template_scope(self):
        details = web_workbench.detect_workflow_details(
            "把这份首访材料改写成督导讨论用的个案背景，按BPS整理已知事实、信息缺口、保护因素和风险追问，"
            "而不是固定初访总结模板。"
        )

        self.assertEqual(details["workflow"], "W2")
        self.assertEqual(details["route_status"], "mixed_signals")
        self.assertEqual(details["top_candidates"][0]["workflow"], "W2")
        self.assertEqual(details["top_candidates"][1]["workflow"], "W1")
        self.assertIn("case background", details["route_notice"].lower())

    def test_detect_workflow_prefers_w6_when_bilingual_roadmap_request_uses_session_note_as_source_material(self):
        details = web_workbench.detect_workflow_details(
            "请把今天的session note作为素材，整理接下来几次咨询的路线图，"
            "包含 immediate next session 和 later phases，保留风险检查点，不要写成咨询记录。"
        )

        self.assertEqual(details["workflow"], "W6")
        self.assertEqual(details["route_status"], "mixed_signals")
        self.assertEqual(details["top_candidates"][0]["workflow"], "W6")
        self.assertEqual(details["top_candidates"][1]["workflow"], "W3")
        self.assertIn("roadmap", details["route_notice"].lower())

    def test_detect_workflow_routes_diagnosis_requests_back_to_case_summary_boundaries(self):
        self.assertEqual(
            web_workbench.detect_workflow(
                "The counselor wants help organizing the case and diagnosis questions after an intake, including risk signals and missing facts."
            ),
            "W2",
        )

    def test_apply_output_style_uses_clean_english_instruction_label(self):
        result = web_workbench.apply_output_style("Base prompt", style="professional_concise")

        self.assertIn("Output style requirement:", result)
        self.assertIn("Match the user's language", result)

    def test_handle_demo_catalog_uses_english_validation_prompts(self):
        status, _headers, body = web_workbench.handle_demo_catalog()

        payload = json.loads(body.decode("utf-8"))
        self.assertEqual(status, 200)
        self.assertIn("Please organize this de-identified biopsychosocial case background.", payload["scenarios"][0]["input"])
        self.assertIn("Create an intake information guide", payload["scenarios"][1]["input"])
        scenario_ids = {item["id"] for item in payload["scenarios"]}
        self.assertIn("initial-interview-material-to-bps-background", scenario_ids)
        self.assertIn("conceptualization-bilingual-session-note-boundary", scenario_ids)
        self.assertIn("roadmap-bilingual-session-note-source-material", scenario_ids)

    def test_handle_run_auto_detects_workflow(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "agent-runs" / "run-1"
            run_dir.mkdir(parents=True)
            (run_dir / "clean_output.md").write_text("clean answer", encoding="utf-8")
            (run_dir / "metadata.json").write_text('{"status": "success"}', encoding="utf-8")

            fake_result = web_workbench.AgentRunResult("W3", "success", run_dir)
            with patch.object(web_workbench, "run_agent_once", return_value=fake_result) as fake_run:
                status, _headers, body = web_workbench.handle_api_run(
                    {"workflow": "AUTO", "input": "本次咨询记录：来访者情绪低落。"}
                )

        payload = json.loads(body.decode("utf-8"))
        self.assertEqual(status, 200)
        self.assertEqual(payload["detected_workflow"], "W3")
        self.assertEqual(fake_run.call_args.args[0], "W3")
        self.assertEqual(payload["route_status"], "clear")
        self.assertIn("Session note", payload["route_notice"])

    def test_handle_run_returns_w1_summary_mode_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "agent-runs" / "run-1"
            run_dir.mkdir(parents=True)
            (run_dir / "clean_output.md").write_text("summary answer", encoding="utf-8")
            (run_dir / "metadata.json").write_text('{"status":"success","w1_mode":"initial_interview_summary"}', encoding="utf-8")
            (
                run_dir / "structured_output.json"
            ).write_text(
                json.dumps(
                    {
                        "workflow": "W1",
                        "document_type": "initial_session_summary",
                        "sections": [
                            {
                                "id": "main_distress",
                                "heading": "Main distress",
                                "known_facts": ["Sleep worsened after the breakup."],
                                "unclear_or_missing": ["Duration of the low mood was not documented."],
                                "follow_up_questions": ["Ask when the sleep change started."],
                            },
                            {
                                "id": "risk_crisis",
                                "heading": "Risk and crisis information",
                                "known_facts": ["Notes mention passive disappearance language without a plan."],
                                "unclear_or_missing": ["Access to means and prior attempts were not documented."],
                                "follow_up_questions": ["Ask about self-harm history, plan, means, and protective factors."],
                            },
                        ],
                        "summary_guidance": ["Separate known facts, unclear or missing facts, and follow-up questions."],
                        "boundary_notes": ["Organize only provided material."],
                    }
                ),
                encoding="utf-8",
            )

            fake_result = web_workbench.AgentRunResult("W1", "success", run_dir)
            with patch.object(web_workbench, "run_agent_once", return_value=fake_result):
                status, _headers, body = web_workbench.handle_api_run(
                    {
                        "workflow": "AUTO",
                        "input": "These are completed initial interview notes, not a session record. Organize them into the fixed initial interview summary template.",
                    }
                )

        payload = json.loads(body.decode("utf-8"))
        self.assertEqual(status, 200)
        self.assertEqual(payload["detected_workflow"], "W1")
        self.assertEqual(payload["w1_mode"], "initial_interview_summary")
        self.assertIn("summary", payload["route_notice"].lower())
        self.assertEqual(payload["w1_summary_brief"]["main_distress"], "Sleep worsened after the breakup.")
        self.assertIn("passive disappearance language", payload["w1_summary_brief"]["risk_highlight"].lower())

    def test_handle_run_returns_route_explanation_summary_for_auto_route(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "agent-runs" / "run-1"
            run_dir.mkdir(parents=True)
            (run_dir / "clean_output.md").write_text("summary answer", encoding="utf-8")
            (run_dir / "metadata.json").write_text('{"status":"success","w1_mode":"initial_interview_summary"}', encoding="utf-8")

            fake_result = web_workbench.AgentRunResult("W1", "success", run_dir)
            with patch.object(web_workbench, "run_agent_once", return_value=fake_result):
                status, _headers, body = web_workbench.handle_api_run(
                    {
                        "workflow": "AUTO",
                        "input": "请把 first interview notes 整理成固定初访总结模板，不要写成 session note。",
                    }
                )

        payload = json.loads(body.decode("utf-8"))
        self.assertEqual(status, 200)
        self.assertIn("routing_reasons_summary", payload)
        self.assertIn("W1", payload["routing_reasons_summary"])
        self.assertIn("W3", payload["routing_reasons_summary"])

    def test_handle_run_returns_w3_birp_brief_for_product_ui(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "agent-runs" / "run-1"
            run_dir.mkdir(parents=True)
            (run_dir / "clean_output.md").write_text("birp answer", encoding="utf-8")
            (run_dir / "metadata.json").write_text('{"status":"success"}', encoding="utf-8")
            (run_dir / "structured_output.json").write_text(
                json.dumps(
                    {
                        "workflow": "W3",
                        "document_type": "session_note",
                        "title": "BIRP counseling record",
                        "record_format": "BIRP",
                        "sections": [
                            {
                                "id": "behavior",
                                "heading": "Behavior",
                                "content": "Client described crying after a conflict with her roommate and sleeping poorly for three nights.",
                            },
                            {
                                "id": "intervention",
                                "heading": "Intervention",
                                "content": "Counselor reviewed grounding steps and clarified confidentiality limits for shared notes.",
                            },
                            {
                                "id": "response",
                                "heading": "Response",
                                "content": "Client said the grounding review felt usable and agreed to text a friend tonight if distress rises.",
                            },
                            {
                                "id": "plan",
                                "heading": "Plan",
                                "content": "Revisit the roommate conflict, sleep disruption, and coping follow-through next session.",
                            },
                            {
                                "id": "risk_change",
                                "heading": "Risk change",
                                "content": "No current suicide plan or intent was reported; earlier passive disappearance wording remained relevant to monitor.",
                            },
                        ],
                        "risk_change": {
                            "content": "No current suicide plan or intent was reported; earlier passive disappearance wording remained relevant to monitor.",
                            "change_documentation": [
                                "Compared with the earlier passive disappearance wording, the current note documents no new escalation to plan or intent."
                            ],
                            "follow_up_actions": [
                                "Re-check ideation, supports, and access to means if distress rises or details stay unclear."
                            ],
                        },
                        "next_session_focus": ["Review coping follow-through and the roommate conflict trigger."],
                        "missing_information": ["The source note did not include direct counselor observation beyond the described intervention."],
                        "boundary_notes": ["This is a counselor-facing record, not a diagnosis or final risk judgment."],
                    }
                ),
                encoding="utf-8",
            )

            fake_result = web_workbench.AgentRunResult("W3", "success", run_dir)
            with patch.object(web_workbench, "run_agent_once", return_value=fake_result):
                status, _headers, body = web_workbench.handle_api_run(
                    {
                        "workflow": "AUTO",
                        "input": "Write a BIRP counseling record from today's de-identified session note with a risk update.",
                    }
                )

        payload = json.loads(body.decode("utf-8"))
        self.assertEqual(status, 200)
        self.assertEqual(payload["detected_workflow"], "W3")
        self.assertIn("w3_record_brief", payload)
        self.assertEqual(payload["w3_record_brief"]["record_format"], "BIRP")
        self.assertIn("crying after a conflict", payload["w3_record_brief"]["behavior_highlight"].lower())
        self.assertIn("no current suicide plan", payload["w3_record_brief"]["risk_highlight"].lower())
        self.assertIn("coping follow-through", payload["w3_record_brief"]["next_focus"].lower())

    def test_handle_run_returns_w1_prep_mode_summary_for_product_ui(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "agent-runs" / "run-1"
            run_dir.mkdir(parents=True)
            (run_dir / "clean_output.md").write_text("prep answer", encoding="utf-8")
            (run_dir / "metadata.json").write_text('{"status":"success","w1_mode":"intake_prep"}', encoding="utf-8")
            (run_dir / "structured_output.json").write_text(
                json.dumps(
                    {
                        "workflow": "W1",
                        "document_type": "intake_form",
                        "known_clues": ["poor sleep for two weeks", "roommate conflict"],
                    }
                ),
                encoding="utf-8",
            )

            fake_result = web_workbench.AgentRunResult("W1", "success", run_dir)
            with patch.object(web_workbench, "run_agent_once", return_value=fake_result):
                status, _headers, body = web_workbench.handle_api_run(
                    {
                        "workflow": "AUTO",
                        "input": "Before tomorrow's first interview, create an intake question guide. "
                        "The client has had poor sleep for two weeks and more conflict with her roommate.",
                    }
                )

        payload = json.loads(body.decode("utf-8"))
        self.assertEqual(status, 200)
        self.assertEqual(payload["w1_mode"], "intake_prep")
        self.assertEqual(payload["workflow_mode_label"], "Initial interview prep")
        self.assertIn("prefill", payload["workflow_mode_notice"].lower())
        self.assertIn("poor sleep for two weeks", payload["workflow_mode_notice"].lower())

    def test_handle_login_sets_session_cookie(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = WorkbenchStore(Path(tmp) / "workbench.sqlite3", Path(tmp) / "uploads")
            with patch.object(web_workbench, "STORE", store):
                with patch.object(web_workbench, "RUN_LOG_PATH", Path(tmp) / "run-log.jsonl"):
                    status, headers, body = web_workbench.handle_login(
                        {"username": "demo", "password": "demo123"}
                    )

        payload = json.loads(body.decode("utf-8"))
        self.assertEqual(status, 200)
        self.assertEqual(payload["status"], "success")
        self.assertIn("Set-Cookie", headers)
        self.assertIn(web_workbench.SESSION_COOKIE, headers["Set-Cookie"])

    def test_handle_login_marks_cookie_secure_on_https(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = WorkbenchStore(Path(tmp) / "workbench.sqlite3", Path(tmp) / "uploads")
            handler = FakeHandler({"X-Forwarded-Proto": "https"})
            with patch.object(web_workbench, "STORE", store):
                with patch.object(web_workbench, "RUN_LOG_PATH", Path(tmp) / "run-log.jsonl"):
                    status, headers, _body = web_workbench.handle_login(
                        {"username": "demo", "password": "demo123"},
                        handler=handler,
                    )

        self.assertEqual(status, 200)
        self.assertIn("Secure", headers["Set-Cookie"])

    def test_handle_session_reports_signup_policy(self):
        handler = FakeHandler()
        with patch.dict(
            "os.environ",
            {"WORKBENCH_SIGNUP_INVITE_CODE": "invite-123", "WORKBENCH_RETENTION_DAYS": "14"},
            clear=False,
        ):
            status, _headers, body = web_workbench.handle_session(handler)

        payload = json.loads(body.decode("utf-8"))
        self.assertEqual(status, 200)
        self.assertFalse(payload["authenticated"])
        self.assertTrue(payload["auth_config"]["signup_enabled"])
        self.assertTrue(payload["auth_config"]["invite_required"])
        self.assertEqual(payload["workspace_policy"]["retention_days"], 14)
        self.assertIn("deployment_readiness", payload)

    def test_handle_session_reports_pilot_ready_deployment_diagnostics(self):
        handler = FakeHandler()
        with patch.dict(
            "os.environ",
            {
                "DEEPSEEK_API_KEY": "sk-live",
                "WORKBENCH_USER": "pilot",
                "WORKBENCH_PASSWORD": "pilot-pass-123",
                "WORKBENCH_ALLOW_SIGNUP": "true",
                "WORKBENCH_SIGNUP_INVITE_CODE": "invite-123",
                "WORKBENCH_RETENTION_DAYS": "14",
            },
            clear=True,
        ):
            status, _headers, body = web_workbench.handle_session(handler)

        payload = json.loads(body.decode("utf-8"))
        self.assertEqual(status, 200)
        readiness = payload["deployment_readiness"]
        self.assertTrue(readiness["pilot_ready"])
        self.assertEqual(readiness["summary"]["fail_count"], 0)
        self.assertEqual(readiness["summary"]["warn_count"], 1)
        checks = {item["id"]: item for item in readiness["checks"]}
        self.assertEqual(checks["deepseek_api"]["status"], "pass")
        self.assertEqual(checks["operator_auth"]["status"], "pass")
        self.assertEqual(checks["workspace_signup"]["status"], "pass")
        self.assertEqual(checks["retention_window"]["status"], "pass")
        self.assertEqual(checks["storage_durability"]["status"], "warn")

    def test_handle_session_flags_missing_key_and_default_credentials(self):
        handler = FakeHandler()
        with patch.dict("os.environ", {}, clear=True):
            status, _headers, body = web_workbench.handle_session(handler)

        payload = json.loads(body.decode("utf-8"))
        self.assertEqual(status, 200)
        readiness = payload["deployment_readiness"]
        self.assertFalse(readiness["pilot_ready"])
        self.assertEqual(readiness["summary"]["fail_count"], 2)
        checks = {item["id"]: item for item in readiness["checks"]}
        self.assertEqual(checks["deepseek_api"]["status"], "fail")
        self.assertEqual(checks["operator_auth"]["status"], "fail")
        self.assertEqual(checks["workspace_signup"]["status"], "warn")

    def test_static_index_includes_deployment_readiness_summary(self):
        index_path = web_workbench.resolve_static_path("/")
        html = index_path.read_text(encoding="utf-8")

        self.assertIn('id="deploymentReadinessSummary"', html)
        self.assertIn('id="accountSummary"', html)
        self.assertIn('id="changePasswordButton"', html)
        self.assertIn("Deployment readiness", html)

    def test_handle_signup_requires_enabled_policy(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = WorkbenchStore(Path(tmp) / "workbench.sqlite3", Path(tmp) / "uploads")
            with patch.object(web_workbench, "STORE", store):
                with patch.dict("os.environ", {}, clear=True):
                    status, _headers, body = web_workbench.handle_signup(
                        {"username": "pilot.user", "password": "safe-pass-123", "password_confirm": "safe-pass-123"}
                    )

        payload = json.loads(body.decode("utf-8"))
        self.assertEqual(status, 403)
        self.assertIn("disabled", payload["message"])

    def test_handle_signup_requires_matching_invite_code(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = WorkbenchStore(Path(tmp) / "workbench.sqlite3", Path(tmp) / "uploads")
            with patch.object(web_workbench, "STORE", store):
                with patch.dict("os.environ", {"WORKBENCH_SIGNUP_INVITE_CODE": "invite-123"}, clear=False):
                    status, _headers, body = web_workbench.handle_signup(
                        {
                            "username": "pilot.user",
                            "password": "safe-pass-123",
                            "password_confirm": "safe-pass-123",
                            "invite_code": "wrong-code",
                        }
                    )

        payload = json.loads(body.decode("utf-8"))
        self.assertEqual(status, 403)
        self.assertIn("Invite code is invalid", payload["message"])

    def test_handle_signup_creates_user_and_session_cookie(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = WorkbenchStore(Path(tmp) / "workbench.sqlite3", Path(tmp) / "uploads")
            with patch.object(web_workbench, "STORE", store):
                with patch.object(web_workbench, "RUN_LOG_PATH", Path(tmp) / "run-log.jsonl"):
                    with patch.dict(
                        "os.environ",
                        {"WORKBENCH_ALLOW_SIGNUP": "true", "WORKBENCH_SIGNUP_INVITE_CODE": "invite-123"},
                        clear=False,
                    ):
                        status, headers, body = web_workbench.handle_signup(
                            {
                                "username": "pilot.user",
                                "password": "safe-pass-123",
                                "password_confirm": "safe-pass-123",
                                "invite_code": "invite-123",
                            }
                        )

        payload = json.loads(body.decode("utf-8"))
        self.assertEqual(status, 200)
        self.assertEqual(payload["status"], "success")
        self.assertEqual(payload["user"]["username"], "pilot.user")
        self.assertIn("Set-Cookie", headers)

    def test_handle_account_change_password_updates_credentials(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = WorkbenchStore(Path(tmp) / "workbench.sqlite3", Path(tmp) / "uploads")
            created = store.create_user("pilot.user", "safe-pass-123")
            user = {"id": created["id"], "username": created["username"], "role": "counselor"}
            run_log = Path(tmp) / "run-log.jsonl"

            with patch.object(web_workbench, "STORE", store):
                with patch.object(web_workbench, "RUN_LOG_PATH", run_log):
                    status, _headers, body = web_workbench.handle_account(
                        user,
                        {
                            "action": "change_password",
                            "current_password": "safe-pass-123",
                            "new_password": "safer-pass-456",
                            "new_password_confirm": "safer-pass-456",
                        },
                    )

            old_auth = store.authenticate("pilot.user", "safe-pass-123")
            new_auth = store.authenticate("pilot.user", "safer-pass-456")
            audit_logs = store.list_audit_logs(user["id"])

        payload = json.loads(body.decode("utf-8"))
        self.assertEqual(status, 200)
        self.assertEqual(payload["status"], "success")
        self.assertIn("Password updated", payload["message"])
        self.assertIsNone(old_auth)
        self.assertEqual(new_auth["user"]["username"], "pilot.user")
        self.assertTrue(any(item["action"] == "auth.password_change" for item in audit_logs))

    def test_handle_account_change_password_requires_matching_confirmation(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = WorkbenchStore(Path(tmp) / "workbench.sqlite3", Path(tmp) / "uploads")
            created = store.create_user("pilot.user", "safe-pass-123")
            user = {"id": created["id"], "username": created["username"], "role": "counselor"}

            with patch.object(web_workbench, "STORE", store):
                status, _headers, body = web_workbench.handle_account(
                    user,
                    {
                        "action": "change_password",
                        "current_password": "safe-pass-123",
                        "new_password": "safer-pass-456",
                        "new_password_confirm": "different-pass-789",
                    },
                )

        payload = json.loads(body.decode("utf-8"))
        self.assertEqual(status, 400)
        self.assertIn("confirmation", payload["message"])

    def test_handle_cases_detail_returns_case_uploads_audit_and_runs(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = WorkbenchStore(Path(tmp) / "workbench.sqlite3", Path(tmp) / "uploads")
            run_log = Path(tmp) / "run-log.jsonl"
            user = {"id": 7, "username": "demo", "role": "counselor"}
            case_record = store.create_case(user["id"], "Case A", client_code="A-001", notes="baseline")
            upload = store.store_upload(
                user["id"],
                "template.docx",
                "ZG9jeA==",
                content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                case_id=case_record["id"],
            )
            store.audit(user["id"], case_record["id"], "workflow.run", {"workflow": "W2"})

            run_log.write_text(
                "\n".join(
                    [
                        json.dumps(
                            {
                                "timestamp": "2026-06-16T10:00:00+00:00",
                                "action": "workflow.run",
                                "user_id": user["id"],
                                "case_id": case_record["id"],
                                "details": {
                                    "workflow": "W2",
                                    "run_dir": r"C:\runs\run-1",
                                    "status": "success",
                                },
                            },
                            ensure_ascii=False,
                        ),
                        json.dumps(
                            {
                                "timestamp": "2026-06-16T11:00:00+00:00",
                                "action": "template.draft",
                                "user_id": user["id"],
                                "case_id": case_record["id"],
                                "details": {
                                    "output_path": r"C:\runs\run-1\filled_template.docx",
                                    "report_path": r"C:\runs\run-1\template_fill_report.json",
                                    "status": "PASS",
                                },
                            },
                            ensure_ascii=False,
                        ),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            with patch.object(web_workbench, "STORE", store):
                with patch.object(web_workbench, "RUN_LOG_PATH", run_log):
                    run_root = Path(tmp) / "agent-runs"
                    run_dir = run_root / "run-1"
                    run_dir.mkdir(parents=True)
                    (run_dir / "clean_output.md").write_text("saved output", encoding="utf-8")
                    store.register_run_artifact(
                        user["id"],
                        str(run_dir),
                        workflow="W2",
                        case_id=case_record["id"],
                        source_action="workflow.run",
                    )
                    status, _headers, body = web_workbench.handle_cases(
                        user,
                        {"action": "detail", "case_id": case_record["id"]},
                    )

        payload = json.loads(body.decode("utf-8"))
        self.assertEqual(status, 200)
        self.assertEqual(payload["case"]["id"], case_record["id"])
        self.assertEqual(payload["uploads"][0]["id"], upload["id"])
        self.assertEqual(payload["audit_logs"][0]["action"], "workflow.run")
        self.assertEqual(payload["recent_runs"][0]["action"], "template.draft")
        self.assertEqual(payload["recent_runs"][1]["details"]["workflow"], "W2")
        self.assertEqual(payload["run_artifacts"][0]["workflow"], "W2")
        self.assertIn("clean_output.md", payload["run_artifacts"][0]["available_files"])

    def test_handle_cases_detail_rejects_unknown_case(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = WorkbenchStore(Path(tmp) / "workbench.sqlite3", Path(tmp) / "uploads")
            user = {"id": 7, "username": "demo", "role": "counselor"}

            with patch.object(web_workbench, "STORE", store):
                status, _headers, body = web_workbench.handle_cases(
                    user,
                    {"action": "detail", "case_id": 999},
                )

        payload = json.loads(body.decode("utf-8"))
        self.assertEqual(status, 404)
        self.assertEqual(payload["message"], "Case not found.")

    def test_handle_cases_export_builds_case_package_zip(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = WorkbenchStore(root / "workbench.sqlite3", root / "uploads")
            auth = store.authenticate("demo", "demo123")
            user = auth["user"]
            case_record = store.create_case(user["id"], "Case Export", client_code="A-101", notes="De-identified notes")
            upload = store.store_upload(
                user["id"],
                "template.docx",
                "ZG9jeA==",
                content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                case_id=case_record["id"],
            )
            store.audit(user["id"], case_record["id"], "workflow.run", {"workflow": "W3"})

            run_root = root / "agent-runs"
            run_dir = run_root / "2026-06-16-W3"
            run_dir.mkdir(parents=True)
            (run_dir / "clean_output.md").write_text("session summary", encoding="utf-8")
            (run_dir / "structured_output.json").write_text('{"workflow":"W3"}', encoding="utf-8")
            (run_dir / "output.docx").write_bytes(b"docx")
            store.register_run_artifact(user["id"], str(run_dir), workflow="W3", case_id=case_record["id"], source_action="workflow.run")

            with patch.object(web_workbench, "STORE", store):
                with patch.object(web_workbench, "RUN_ROOT", run_root):
                    with patch.object(web_workbench, "RUN_LOG_PATH", root / "workbench-run-log.jsonl"):
                        status, _headers, body = web_workbench.handle_cases(
                            user,
                            {"action": "export", "case_id": case_record["id"]},
                        )

            payload = json.loads(body.decode("utf-8"))
            self.assertEqual(status, 200)
            self.assertEqual(payload["status"], "success")
            self.assertTrue(payload["output_path"].endswith(".zip"))
            package_path = Path(payload["output_path"])
            self.assertTrue(package_path.exists())
            with zipfile.ZipFile(package_path) as archive:
                names = set(archive.namelist())
                self.assertIn("case-summary.json", names)
                self.assertIn("audit-log.json", names)
                self.assertIn("recent-runs.json", names)
                self.assertIn("uploads/template.docx", names)
                self.assertIn("runs/2026-06-16-W3/clean_output.md", names)
                self.assertIn("runs/2026-06-16-W3/output.docx", names)
                summary = json.loads(archive.read("case-summary.json").decode("utf-8"))
            self.assertEqual(summary["case"]["client_code"], "A-101")
            self.assertEqual(summary["artifacts"]["upload_count"], 1)
            self.assertEqual(summary["artifacts"]["run_count"], 1)

    def test_handle_cases_export_rejects_unknown_case(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = WorkbenchStore(Path(tmp) / "workbench.sqlite3", Path(tmp) / "uploads")
            user = {"id": 7, "username": "demo", "role": "counselor"}

            with patch.object(web_workbench, "STORE", store):
                status, _headers, body = web_workbench.handle_cases(
                    user,
                    {"action": "export", "case_id": 999},
                )

        payload = json.loads(body.decode("utf-8"))
        self.assertEqual(status, 404)
        self.assertEqual(payload["message"], "Case not found.")

    def test_handle_cases_delete_removes_case_files_runs_and_recent_activity(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = WorkbenchStore(root / "workbench.sqlite3", root / "uploads")
            auth = store.authenticate("demo", "demo123")
            user = auth["user"]
            case_record = store.create_case(user["id"], "Delete Case", client_code="DEL-101", notes="remove")
            keep_case = store.create_case(user["id"], "Keep Case", client_code="KEEP-101", notes="stay")

            deleted_upload = store.store_upload(
                user["id"],
                "delete.docx",
                "ZG9jeA==",
                content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                case_id=case_record["id"],
            )
            kept_upload = store.store_upload(
                user["id"],
                "keep.docx",
                "a2VlcA==",
                content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                case_id=keep_case["id"],
            )
            store.audit(user["id"], case_record["id"], "workflow.run", {"workflow": "W2"})
            store.audit(user["id"], keep_case["id"], "workflow.run", {"workflow": "W1"})

            run_root = root / "agent-runs"
            delete_run = run_root / "delete-run"
            keep_run = run_root / "keep-run"
            delete_run.mkdir(parents=True)
            keep_run.mkdir(parents=True)
            (delete_run / "clean_output.md").write_text("delete", encoding="utf-8")
            (keep_run / "clean_output.md").write_text("keep", encoding="utf-8")
            store.register_run_artifact(user["id"], str(delete_run), workflow="W2", case_id=case_record["id"], source_action="workflow.run")
            store.register_run_artifact(user["id"], str(keep_run), workflow="W1", case_id=keep_case["id"], source_action="workflow.run")

            run_log = root / "workbench-run-log.jsonl"
            run_log.write_text(
                "\n".join(
                    [
                        json.dumps(
                            {
                                "timestamp": "2026-06-16T10:00:00+00:00",
                                "action": "workflow.run",
                                "user_id": user["id"],
                                "case_id": case_record["id"],
                                "details": {"run_dir": str(delete_run), "status": "success"},
                            },
                            ensure_ascii=False,
                        ),
                        json.dumps(
                            {
                                "timestamp": "2026-06-16T10:05:00+00:00",
                                "action": "workflow.run",
                                "user_id": user["id"],
                                "case_id": keep_case["id"],
                                "details": {"run_dir": str(keep_run), "status": "success"},
                            },
                            ensure_ascii=False,
                        ),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            with patch.object(web_workbench, "STORE", store):
                with patch.object(web_workbench, "RUN_ROOT", run_root):
                    with patch.object(web_workbench, "RUN_LOG_PATH", run_log):
                        status, _headers, body = web_workbench.handle_cases(
                            user,
                            {"action": "delete", "case_id": case_record["id"]},
                        )

            payload = json.loads(body.decode("utf-8"))
            self.assertEqual(status, 200)
            self.assertEqual(payload["status"], "success")
            self.assertEqual(payload["deleted_case"]["title"], "Delete Case")
            self.assertEqual(payload["summary"]["counts"]["uploads"], 1)
            self.assertEqual(payload["summary"]["counts"]["audit_logs"], 3)
            self.assertFalse(Path(deleted_upload["stored_path"]).exists())
            self.assertTrue(Path(kept_upload["stored_path"]).exists())
            self.assertFalse(delete_run.exists())
            self.assertTrue(keep_run.exists())
            self.assertEqual(store.list_cases(user["id"])[0]["title"], "Keep Case")
            remaining_entries = [
                json.loads(line)
                for line in run_log.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            self.assertTrue(any(entry["action"] == "case.delete" for entry in remaining_entries))
            self.assertFalse(any(entry.get("case_id") == case_record["id"] and entry["action"] == "workflow.run" for entry in remaining_entries))
            self.assertTrue(any(entry.get("case_id") == keep_case["id"] for entry in remaining_entries))

    def test_handle_workspace_export_builds_backup_zip(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = WorkbenchStore(root / "workbench.sqlite3", root / "uploads")
            auth = store.authenticate("demo", "demo123")
            user = auth["user"]
            case_record = store.create_case(user["id"], "Workspace Export", client_code="WS-001", notes="backup")
            store.store_upload(
                user["id"],
                "template.docx",
                "ZG9jeA==",
                content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                case_id=case_record["id"],
            )
            store.audit(user["id"], case_record["id"], "workflow.run", {"workflow": "W2"})

            run_root = root / "agent-runs"
            run_dir = run_root / "2026-06-16-W2"
            run_dir.mkdir(parents=True)
            (run_dir / "clean_output.md").write_text("case summary", encoding="utf-8")
            store.register_run_artifact(
                user["id"],
                str(run_dir),
                workflow="W2",
                case_id=case_record["id"],
                source_action="workflow.run",
            )

            run_log = root / "workbench-run-log.jsonl"
            run_log.write_text(
                json.dumps(
                    {
                        "timestamp": "2026-06-16T10:00:00+00:00",
                        "action": "workflow.run",
                        "user_id": user["id"],
                        "case_id": case_record["id"],
                        "details": {"run_dir": str(run_dir), "status": "success"},
                    },
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )

            with patch.object(web_workbench, "STORE", store):
                with patch.object(web_workbench, "RUN_ROOT", run_root):
                    with patch.object(web_workbench, "RUN_LOG_PATH", run_log):
                        status, _headers, body = web_workbench.handle_workspace(user, {"action": "export"})
            payload = json.loads(body.decode("utf-8"))
            self.assertEqual(status, 200)
            self.assertEqual(payload["status"], "success")
            backup_path = Path(payload["output_path"])
            self.assertTrue(backup_path.exists())
            with zipfile.ZipFile(backup_path) as archive:
                names = set(archive.namelist())
                self.assertIn("manifest.json", names)
                self.assertIn("workspace.json", names)
                self.assertIn("uploads/template.docx", names)
                self.assertIn("runs/2026-06-16-W2/clean_output.md", names)
                manifest = json.loads(archive.read("manifest.json").decode("utf-8"))
                workspace = json.loads(archive.read("workspace.json").decode("utf-8"))
            self.assertEqual(manifest["counts"]["cases"], 1)
            self.assertEqual(workspace["cases"][0]["client_code"], "WS-001")
            self.assertEqual(workspace["recent_activity"][0]["action"], "workflow.run")

    def test_handle_workspace_restore_replaces_existing_workspace(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = WorkbenchStore(root / "workbench.sqlite3", root / "uploads")
            auth = store.authenticate("demo", "demo123")
            user = auth["user"]
            stale_case = store.create_case(user["id"], "Stale Case", client_code="OLD-1", notes="old")
            stale_upload = store.store_upload(user["id"], "old.txt", base64.b64encode(b"old").decode("ascii"), case_id=stale_case["id"])
            stale_run_root = root / "agent-runs"
            stale_run_dir = stale_run_root / "old-run"
            stale_run_dir.mkdir(parents=True)
            (stale_run_dir / "clean_output.md").write_text("old", encoding="utf-8")
            store.register_run_artifact(user["id"], str(stale_run_dir), workflow="W1", case_id=stale_case["id"], source_action="workflow.run")
            run_log = root / "workbench-run-log.jsonl"
            run_log.write_text(
                json.dumps(
                    {
                        "timestamp": "2026-06-10T09:00:00+00:00",
                        "action": "workflow.run",
                        "user_id": user["id"],
                        "case_id": stale_case["id"],
                        "details": {"run_dir": str(stale_run_dir), "stored_path": stale_upload["stored_path"]},
                    },
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )

            backup_path = root / "workspace-backup.zip"
            workspace_payload = {
                "cases": [
                    {
                        "id": 41,
                        "title": "Restored Case",
                        "client_code": "RESTORE-41",
                        "notes": "restored notes",
                        "created_at": "2026-06-01T10:00:00+00:00",
                        "updated_at": "2026-06-02T10:00:00+00:00",
                    }
                ],
                "uploads": [
                    {
                        "id": 9,
                        "case_id": 41,
                        "original_name": "restored-template.docx",
                        "content_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        "size_bytes": 4,
                        "created_at": "2026-06-03T10:00:00+00:00",
                        "archive_path": "uploads/restored-template.docx",
                        "stored_path": "C:/old/uploads/restored-template.docx",
                    }
                ],
                "audit_logs": [
                    {
                        "case_id": 41,
                        "action": "workflow.run",
                        "details": {"run_dir": "C:/old-runs/run-restore"},
                        "created_at": "2026-06-04T10:00:00+00:00",
                    }
                ],
                "run_artifacts": [
                    {
                        "run_dir": "C:/old-runs/run-restore",
                        "run_name": "run-restore",
                        "case_id": 41,
                        "workflow": "W2",
                        "source_action": "workflow.run",
                        "created_at": "2026-06-05T10:00:00+00:00",
                        "files": ["clean_output.md"],
                    }
                ],
                "recent_activity": [
                    {
                        "timestamp": "2026-06-06T10:00:00+00:00",
                        "action": "workflow.run",
                        "user_id": user["id"],
                        "case_id": 41,
                        "details": {
                            "run_dir": "C:/old-runs/run-restore",
                            "stored_path": "C:/old/uploads/restored-template.docx",
                            "status": "success",
                        },
                    }
                ],
            }
            with zipfile.ZipFile(backup_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                archive.writestr(
                    "manifest.json",
                    json.dumps({"version": 1, "counts": {"cases": 1, "uploads": 1, "runs": 1}}, ensure_ascii=False),
                )
                archive.writestr("workspace.json", json.dumps(workspace_payload, ensure_ascii=False))
                archive.writestr("uploads/restored-template.docx", b"docx")
                archive.writestr("runs/run-restore/clean_output.md", "restored output")

            with patch.object(web_workbench, "STORE", store):
                with patch.object(web_workbench, "RUN_ROOT", stale_run_root):
                    with patch.object(web_workbench, "RUN_LOG_PATH", run_log):
                        status, _headers, body = web_workbench.handle_workspace(
                            user,
                            {
                                "action": "restore",
                                "backup_base64": base64.b64encode(backup_path.read_bytes()).decode("ascii"),
                            },
                        )
                        recent = web_workbench.list_recent_runs(user["id"], limit=10)

            payload = json.loads(body.decode("utf-8"))
            cases = store.list_cases(user["id"])
            uploads = store.list_uploads(user["id"])
            runs = store.list_run_artifacts(user["id"])
            restored_upload_exists = Path(uploads[0]["stored_path"]).exists()
            restored_run_output_exists = (Path(runs[0]["run_dir"]) / "clean_output.md").exists()
            stale_upload_exists = Path(stale_upload["stored_path"]).exists()

        self.assertEqual(status, 200)
        self.assertEqual(payload["status"], "success")
        self.assertEqual(len(cases), 1)
        self.assertEqual(cases[0]["title"], "Restored Case")
        self.assertEqual(cases[0]["client_code"], "RESTORE-41")
        self.assertEqual(len(uploads), 1)
        self.assertTrue(restored_upload_exists)
        self.assertNotIn("old-run", runs[0]["run_dir"])
        self.assertTrue(restored_run_output_exists)
        self.assertEqual(recent[0]["action"], "workflow.run")
        self.assertEqual(recent[0]["details"]["status"], "success")
        self.assertNotIn("old-run", recent[0]["details"]["run_dir"])
        self.assertFalse(stale_upload_exists)

    def test_handle_workspace_restore_missing_artifact_keeps_existing_workspace(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = WorkbenchStore(root / "workbench.sqlite3", root / "uploads")
            auth = store.authenticate("demo", "demo123")
            user = auth["user"]
            existing_case = store.create_case(user["id"], "Keep Me", client_code="KEEP-1", notes="existing")
            existing_upload = store.store_upload(
                user["id"],
                "keep.docx",
                base64.b64encode(b"keep").decode("ascii"),
                case_id=existing_case["id"],
            )
            run_root = root / "agent-runs"
            existing_run_dir = run_root / "keep-run"
            existing_run_dir.mkdir(parents=True)
            (existing_run_dir / "clean_output.md").write_text("keep", encoding="utf-8")
            store.register_run_artifact(
                user["id"],
                str(existing_run_dir),
                workflow="W2",
                case_id=existing_case["id"],
                source_action="workflow.run",
            )
            run_log = root / "workbench-run-log.jsonl"
            run_log.write_text(
                json.dumps(
                    {
                        "timestamp": "2026-06-10T09:00:00+00:00",
                        "action": "workflow.run",
                        "user_id": user["id"],
                        "case_id": existing_case["id"],
                        "details": {"run_dir": str(existing_run_dir), "stored_path": existing_upload["stored_path"]},
                    },
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )

            backup_path = root / "workspace-backup.zip"
            workspace_payload = {
                "cases": [{"id": 41, "title": "Broken Restore", "client_code": "BROKEN-41", "notes": ""}],
                "uploads": [],
                "audit_logs": [],
                "run_artifacts": [
                    {
                        "run_dir": "C:/old-runs/run-restore",
                        "run_name": "run-restore",
                        "case_id": 41,
                        "workflow": "W2",
                        "source_action": "workflow.run",
                        "created_at": "2026-06-05T10:00:00+00:00",
                        "files": ["clean_output.md"],
                    }
                ],
                "recent_activity": [],
            }
            with zipfile.ZipFile(backup_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                archive.writestr(
                    "manifest.json",
                    json.dumps({"version": 1, "counts": {"cases": 1, "uploads": 0, "runs": 1}}, ensure_ascii=False),
                )
                archive.writestr("workspace.json", json.dumps(workspace_payload, ensure_ascii=False))

            with patch.object(web_workbench, "STORE", store):
                with patch.object(web_workbench, "RUN_ROOT", run_root):
                    with patch.object(web_workbench, "RUN_LOG_PATH", run_log):
                        status, _headers, body = web_workbench.handle_workspace(
                            user,
                            {
                                "action": "restore",
                                "backup_base64": base64.b64encode(backup_path.read_bytes()).decode("ascii"),
                            },
                        )
                        payload = json.loads(body.decode("utf-8"))
                        self.assertEqual(status, 400)
                        self.assertIn("runs/run-restore/clean_output.md", payload["message"])
                        self.assertEqual(store.list_cases(user["id"])[0]["title"], "Keep Me")
                        self.assertTrue(Path(existing_upload["stored_path"]).exists())
                        self.assertTrue((existing_run_dir / "clean_output.md").exists())
                        self.assertEqual(len(store.list_run_artifacts(user["id"])), 1)

    def test_handle_workspace_restore_invalid_upload_name_keeps_existing_workspace(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = WorkbenchStore(root / "workbench.sqlite3", root / "uploads")
            auth = store.authenticate("demo", "demo123")
            user = auth["user"]
            existing_case = store.create_case(user["id"], "Keep Me", client_code="KEEP-2", notes="existing")
            existing_upload = store.store_upload(
                user["id"],
                "keep.docx",
                base64.b64encode(b"keep").decode("ascii"),
                case_id=existing_case["id"],
            )
            run_root = root / "agent-runs"
            existing_run_dir = run_root / "keep-run"
            existing_run_dir.mkdir(parents=True)
            (existing_run_dir / "clean_output.md").write_text("keep", encoding="utf-8")
            store.register_run_artifact(
                user["id"],
                str(existing_run_dir),
                workflow="W2",
                case_id=existing_case["id"],
                source_action="workflow.run",
            )
            run_log = root / "workbench-run-log.jsonl"
            run_log.write_text("", encoding="utf-8")

            backup_path = root / "workspace-backup.zip"
            workspace_payload = {
                "cases": [{"id": 51, "title": "Broken Upload", "client_code": "BROKEN-51", "notes": ""}],
                "uploads": [
                    {
                        "id": 11,
                        "case_id": 51,
                        "original_name": "../escape.docx",
                        "content_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        "size_bytes": 4,
                        "created_at": "2026-06-03T10:00:00+00:00",
                        "archive_path": "uploads/escape.docx",
                        "stored_path": "C:/old/uploads/escape.docx",
                    }
                ],
                "audit_logs": [],
                "run_artifacts": [],
                "recent_activity": [],
            }
            with zipfile.ZipFile(backup_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                archive.writestr(
                    "manifest.json",
                    json.dumps({"version": 1, "counts": {"cases": 1, "uploads": 1, "runs": 0}}, ensure_ascii=False),
                )
                archive.writestr("workspace.json", json.dumps(workspace_payload, ensure_ascii=False))
                archive.writestr("uploads/escape.docx", b"docx")

            with patch.object(web_workbench, "STORE", store):
                with patch.object(web_workbench, "RUN_ROOT", run_root):
                    with patch.object(web_workbench, "RUN_LOG_PATH", run_log):
                        status, _headers, body = web_workbench.handle_workspace(
                            user,
                            {
                                "action": "restore",
                                "backup_base64": base64.b64encode(backup_path.read_bytes()).decode("ascii"),
                            },
                        )
                        payload = json.loads(body.decode("utf-8"))
                        self.assertEqual(status, 400)
                        self.assertIn("Unsafe upload file name", payload["message"])
                        self.assertEqual(store.list_cases(user["id"])[0]["title"], "Keep Me")
                        self.assertTrue(Path(existing_upload["stored_path"]).exists())
                        self.assertTrue((existing_run_dir / "clean_output.md").exists())
                        self.assertEqual(len(store.list_run_artifacts(user["id"])), 1)

    def test_handle_workspace_status_reports_counts_storage_and_policy(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = WorkbenchStore(root / "workbench.sqlite3", root / "uploads")
            auth = store.authenticate("demo", "demo123")
            user = auth["user"]
            case_record = store.create_case(user["id"], "Status Case")
            store.store_upload(user["id"], "template.docx", base64.b64encode(b"docx").decode("ascii"), case_id=case_record["id"])
            run_root = root / "agent-runs"
            run_dir = run_root / "run-1"
            run_dir.mkdir(parents=True)
            (run_dir / "clean_output.md").write_text("artifact", encoding="utf-8")
            store.register_run_artifact(user["id"], str(run_dir), workflow="W2", case_id=case_record["id"], source_action="workflow.run")

            with patch.object(web_workbench, "STORE", store):
                with patch.object(web_workbench, "RUN_ROOT", run_root):
                    with patch.dict("os.environ", {"WORKBENCH_MAX_UPLOAD_BYTES": "2048", "WORKBENCH_RETENTION_DAYS": "30"}, clear=False):
                        status, _headers, body = web_workbench.handle_workspace(user, {"action": "status"})

        payload = json.loads(body.decode("utf-8"))
        self.assertEqual(status, 200)
        self.assertEqual(payload["policy"]["max_upload_bytes"], 2048)
        self.assertEqual(payload["policy"]["retention_days"], 30)
        self.assertEqual(payload["summary"]["counts"]["cases"], 1)
        self.assertEqual(payload["summary"]["counts"]["uploads"], 1)
        self.assertEqual(payload["summary"]["counts"]["run_artifacts"], 1)
        self.assertGreater(payload["summary"]["storage"]["total_bytes"], 0)

    def test_handle_workspace_prune_removes_expired_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = WorkbenchStore(root / "workbench.sqlite3", root / "uploads")
            auth = store.authenticate("demo", "demo123")
            user = auth["user"]
            case_record = store.create_case(user["id"], "Prune Case")
            stale_upload = store.store_upload(user["id"], "old.docx", base64.b64encode(b"old").decode("ascii"), case_id=case_record["id"])
            kept_upload = store.store_upload(user["id"], "new.docx", base64.b64encode(b"new").decode("ascii"), case_id=case_record["id"])
            run_root = root / "agent-runs"
            stale_run = run_root / "old-run"
            kept_run = run_root / "new-run"
            stale_run.mkdir(parents=True)
            kept_run.mkdir(parents=True)
            store.register_run_artifact(
                user["id"],
                str(stale_run),
                workflow="W1",
                case_id=case_record["id"],
                source_action="workflow.run",
                created_at=(utc_now() - timedelta(days=10)).isoformat(timespec="seconds"),
            )
            store.register_run_artifact(
                user["id"],
                str(kept_run),
                workflow="W2",
                case_id=case_record["id"],
                source_action="workflow.run",
                created_at=utc_now().isoformat(timespec="seconds"),
            )
            store.import_audit_log(
                user["id"],
                case_record["id"],
                "workflow.run",
                {"workflow": "W1"},
                created_at=(utc_now() - timedelta(days=10)).isoformat(timespec="seconds"),
            )
            with store.connect() as conn:
                old_created = (utc_now() - timedelta(days=10)).isoformat(timespec="seconds")
                conn.execute("UPDATE uploads SET created_at = ? WHERE id = ?", (old_created, stale_upload["id"]))
                conn.execute("UPDATE uploads SET created_at = ? WHERE id = ?", (utc_now().isoformat(timespec="seconds"), kept_upload["id"]))
            run_log = root / "workbench-run-log.jsonl"
            run_log.write_text(
                "\n".join(
                    [
                        json.dumps(
                            {
                                "timestamp": (utc_now() - timedelta(days=10)).isoformat(timespec="seconds"),
                                "action": "workflow.run",
                                "user_id": user["id"],
                                "case_id": case_record["id"],
                                "details": {"run_dir": str(stale_run)},
                            },
                            ensure_ascii=False,
                        ),
                        json.dumps(
                            {
                                "timestamp": utc_now().isoformat(timespec="seconds"),
                                "action": "workflow.run",
                                "user_id": user["id"],
                                "case_id": case_record["id"],
                                "details": {"run_dir": str(kept_run)},
                            },
                            ensure_ascii=False,
                        ),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            with patch.object(web_workbench, "STORE", store):
                with patch.object(web_workbench, "RUN_ROOT", run_root):
                    with patch.object(web_workbench, "RUN_LOG_PATH", run_log):
                        with patch.dict("os.environ", {"WORKBENCH_RETENTION_DAYS": "5"}, clear=False):
                            status, _headers, body = web_workbench.handle_workspace(user, {"action": "prune"})

            remaining_entries = [json.loads(line) for line in run_log.read_text(encoding="utf-8").splitlines() if line.strip()]
            stale_upload_exists = Path(stale_upload["stored_path"]).exists()
            kept_upload_exists = Path(kept_upload["stored_path"]).exists()
            stale_run_exists = stale_run.exists()
            kept_run_exists = kept_run.exists()

        payload = json.loads(body.decode("utf-8"))
        self.assertEqual(status, 200)
        self.assertEqual(payload["pruned"]["counts"]["uploads"], 1)
        self.assertEqual(payload["pruned"]["counts"]["run_artifacts"], 1)
        self.assertFalse(stale_upload_exists)
        self.assertTrue(kept_upload_exists)
        self.assertFalse(stale_run_exists)
        self.assertTrue(kept_run_exists)
        self.assertEqual(len(remaining_entries), 2)
        self.assertTrue(any(entry["action"] == "workspace.prune" for entry in remaining_entries))
        self.assertTrue(any(entry["details"].get("run_dir") == str(kept_run) for entry in remaining_entries if entry["action"] == "workflow.run"))

    def test_handle_workspace_reset_requires_confirmation_phrase(self):
        user = {"id": 7, "username": "demo", "role": "counselor"}

        status, _headers, body = web_workbench.handle_workspace(user, {"action": "reset", "confirm_text": "DELETE"})

        payload = json.loads(body.decode("utf-8"))
        self.assertEqual(status, 400)
        self.assertIn("DELETE WORKSPACE", payload["message"])

    def test_handle_workspace_reset_clears_account_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = WorkbenchStore(root / "workbench.sqlite3", root / "uploads")
            auth = store.authenticate("demo", "demo123")
            user = auth["user"]
            case_record = store.create_case(user["id"], "Reset Case")
            upload = store.store_upload(user["id"], "template.docx", base64.b64encode(b"docx").decode("ascii"), case_id=case_record["id"])
            run_root = root / "agent-runs"
            run_dir = run_root / "run-1"
            run_dir.mkdir(parents=True)
            store.register_run_artifact(user["id"], str(run_dir), workflow="W2", case_id=case_record["id"], source_action="workflow.run")
            run_log = root / "workbench-run-log.jsonl"
            run_log.write_text(
                json.dumps(
                    {
                        "timestamp": utc_now().isoformat(timespec="seconds"),
                        "action": "workflow.run",
                        "user_id": user["id"],
                        "case_id": case_record["id"],
                        "details": {"run_dir": str(run_dir), "stored_path": upload["stored_path"]},
                    },
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )

            with patch.object(web_workbench, "STORE", store):
                with patch.object(web_workbench, "RUN_ROOT", run_root):
                    with patch.object(web_workbench, "RUN_LOG_PATH", run_log):
                        status, _headers, body = web_workbench.handle_workspace(
                            user,
                            {"action": "reset", "confirm_text": "DELETE WORKSPACE"},
                        )

            remaining_entries = [json.loads(line) for line in run_log.read_text(encoding="utf-8").splitlines() if line.strip()]
            cases = store.list_cases(user["id"])
            uploads = store.list_uploads(user["id"])
            runs = store.list_run_artifacts(user["id"])
            upload_exists = Path(upload["stored_path"]).exists()
            run_exists = run_dir.exists()

        payload = json.loads(body.decode("utf-8"))
        self.assertEqual(status, 200)
        self.assertEqual(payload["summary"]["counts"]["cases"], 1)
        self.assertEqual(cases, [])
        self.assertEqual(uploads, [])
        self.assertEqual(runs, [])
        self.assertFalse(upload_exists)
        self.assertFalse(run_exists)
        self.assertEqual(len(remaining_entries), 1)
        self.assertEqual(remaining_entries[0]["action"], "workspace.reset")

    def test_handle_upload_rejects_file_over_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = WorkbenchStore(Path(tmp) / "workbench.sqlite3", Path(tmp) / "uploads")
            auth = store.authenticate("demo", "demo123")
            user = auth["user"]
            payload = {
                "filename": "big.docx",
                "content_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "content_base64": base64.b64encode(b"0123456789").decode("ascii"),
            }

            with patch.object(web_workbench, "STORE", store):
                with patch.dict("os.environ", {"WORKBENCH_MAX_UPLOAD_BYTES": "4"}, clear=False):
                    status, _headers, body = web_workbench.handle_upload(user, payload)

        response = json.loads(body.decode("utf-8"))
        self.assertEqual(status, 400)
        self.assertIn("deployment limit", response["message"])

    def test_apply_output_style_adds_style_instruction(self):
        styled = web_workbench.apply_output_style("材料", style="warm_clinical")

        self.assertIn("材料", styled)
        self.assertIn("输出风格要求", styled)
        self.assertIn("温和", styled)

    def test_apply_output_style_leaves_default_input_unchanged(self):
        self.assertEqual(web_workbench.apply_output_style("材料", style="default"), "材料")

    def test_handle_run_returns_saved_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "agent-runs" / "run-1"
            run_dir.mkdir(parents=True)
            (run_dir / "clean_output.md").write_text("clean answer", encoding="utf-8")
            (run_dir / "structured_output.json").write_text('{"workflow": "W1"}', encoding="utf-8")
            (run_dir / "structured_check.json").write_text('{"status": "PASS"}', encoding="utf-8")
            (run_dir / "safety_check.json").write_text(
                '{"status": "PASS", "rubric_status": "PASS"}',
                encoding="utf-8",
            )
            (run_dir / "metadata.json").write_text('{"status": "success"}', encoding="utf-8")

            fake_result = web_workbench.AgentRunResult("W1", "success", run_dir)
            with patch.object(web_workbench, "run_agent_once", return_value=fake_result) as fake_run:
                status, _headers, body = web_workbench.handle_api_run(
                    {
                        "workflow": "W1",
                        "input": "材料",
                        "structured": True,
                        "render_docx": False,
                        "output_style": "institutional_record",
                    }
                )

        payload = json.loads(body.decode("utf-8"))
        self.assertEqual(status, 200)
        self.assertEqual(payload["status"], "success")
        self.assertEqual(payload["workflow"], "W1")
        self.assertEqual(payload["clean_output"], "clean answer")
        self.assertEqual(payload["structured_output"], {"workflow": "W1"})
        self.assertEqual(payload["structured_check"], {"status": "PASS"})
        self.assertIn("机构留档", fake_run.call_args.kwargs["inline_input"])

    def test_handle_run_rejects_unknown_workflow(self):
        with patch.object(
            web_workbench,
            "run_agent_once",
            side_effect=web_workbench.AgentInputError("Unknown workflow `bad`."),
        ):
            status, _headers, body = web_workbench.handle_api_run({"workflow": "bad", "input": "材料"})

        payload = json.loads(body.decode("utf-8"))
        self.assertEqual(status, 400)
        self.assertEqual(payload["message"], "Unknown workflow `bad`.")

    def test_handle_run_hides_unexpected_exception_details(self):
        with patch.object(
            web_workbench,
            "run_agent_once",
            side_effect=RuntimeError("secret provider token"),
        ):
            status, _headers, body = web_workbench.handle_api_run({"workflow": "W1", "input": "材料"})

        payload = json.loads(body.decode("utf-8"))
        self.assertEqual(status, 500)
        self.assertEqual(payload["message"], "Agent run failed.")
        self.assertNotIn("secret provider token", body.decode("utf-8"))

    def test_load_run_payload_tolerates_malformed_json_artifact(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "agent-runs" / "run-1"
            run_dir.mkdir(parents=True)
            (run_dir / "clean_output.md").write_text("clean answer", encoding="utf-8")
            (run_dir / "structured_output.json").write_text("{not valid json", encoding="utf-8")

            result = web_workbench.AgentRunResult("W1", "success", run_dir)
            payload = web_workbench.load_run_payload(result)

        self.assertEqual(payload["status"], "success")
        self.assertEqual(payload["clean_output"], "clean answer")
        self.assertIsNone(payload["structured_output"])
        self.assertTrue(
            any("structured_output.json" in issue["message"] for issue in payload["issues"]),
            payload["issues"],
        )

    def test_handle_render_docx_requires_structured_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_root = Path(tmp) / "agent-runs"
            run_dir = run_root / "run"
            run_dir.mkdir(parents=True)
            with patch.object(web_workbench, "RUN_ROOT", run_root):
                status, _headers, body = web_workbench.handle_render_docx({"run_dir": str(run_dir)})

        self.assertEqual(status, 400)
        self.assertIn("structured_output.json", json.loads(body.decode("utf-8"))["message"])

    def test_handle_render_docx_rejects_run_dir_outside_run_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_root = Path(tmp) / "agent-runs"
            run_root.mkdir()
            run_dir = Path(tmp) / "outside-run"
            run_dir.mkdir()
            (run_dir / "structured_output.json").write_text('{"workflow": "W1"}', encoding="utf-8")

            with patch.object(web_workbench, "RUN_ROOT", run_root):
                status, _headers, body = web_workbench.handle_render_docx({"run_dir": str(run_dir)})

        payload = json.loads(body.decode("utf-8"))
        self.assertEqual(status, 400)
        self.assertIn("outside approved output directory", payload["message"])

    def test_handle_fill_template_uses_current_structured_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = WorkbenchStore(Path(tmp) / "workbench.sqlite3", Path(tmp) / "uploads")
            auth = store.authenticate("demo", "demo123")
            upload = store.store_upload(
                auth["user"]["id"],
                "template.docx",
                "ZG9jeA==",
                content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
            run_root = Path(tmp) / "agent-runs"
            run_dir = run_root / "run"
            run_dir.mkdir(parents=True)
            structured = run_dir / "structured_output.json"
            structured.write_text('{"workflow": "W1"}', encoding="utf-8")
            store.register_run_artifact(auth["user"]["id"], str(run_dir), workflow="W1")

            def fake_fill(template_path, structured_path, output_path, report_path, mapping_path=None):
                Path(output_path).write_bytes(b"filled")
                report = {"status": "PASS", "filled_fields": [{"template_label": "A"}], "unfilled_fields": [], "issues": []}
                Path(report_path).write_text(json.dumps(report), encoding="utf-8")
                return report

            with patch.object(web_workbench, "STORE", store):
                with patch.object(web_workbench, "fill_docx_template", side_effect=fake_fill):
                    with patch.object(web_workbench, "RUN_ROOT", run_root):
                        status, _headers, body = web_workbench.handle_fill_template(
                            {
                                "run_dir": str(run_dir),
                                "template_ref": f"upload:{upload['id']}",
                                "user_id": auth["user"]["id"],
                            }
                        )

        payload = json.loads(body.decode("utf-8"))
        self.assertEqual(status, 200)
        self.assertEqual(payload["status"], "success")
        self.assertTrue(payload["output_path"].endswith("filled_template.docx"))
        self.assertEqual(payload["report"]["status"], "PASS")

    def test_handle_fill_template_can_enable_llm_mapping(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = WorkbenchStore(Path(tmp) / "workbench.sqlite3", Path(tmp) / "uploads")
            auth = store.authenticate("demo", "demo123")
            upload = store.store_upload(
                auth["user"]["id"],
                "template.docx",
                "ZG9jeA==",
                content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
            run_root = Path(tmp) / "agent-runs"
            run_dir = run_root / "run"
            run_dir.mkdir(parents=True)
            structured = run_dir / "structured_output.json"
            structured.write_text('{"workflow": "W3"}', encoding="utf-8")
            store.register_run_artifact(auth["user"]["id"], str(run_dir), workflow="W3")

            def fake_fill(template_path, structured_path, output_path, report_path, mapping_output_path=None):
                Path(output_path).write_bytes(b"filled")
                if mapping_output_path:
                    Path(mapping_output_path).write_text('{"mappings": []}', encoding="utf-8")
                report = {
                    "status": "PASS",
                    "filled_fields": [{"template_label": "A"}],
                    "unfilled_fields": [],
                    "issues": [],
                    "llm_status": "success",
                }
                Path(report_path).write_text(json.dumps(report), encoding="utf-8")
                return report

            with patch.object(web_workbench, "STORE", store):
                with patch.object(web_workbench, "fill_docx_template_with_llm_mapping", side_effect=fake_fill):
                    with patch.object(web_workbench, "RUN_ROOT", run_root):
                        status, _headers, body = web_workbench.handle_fill_template(
                            {
                                "run_dir": str(run_dir),
                                "template_ref": f"upload:{upload['id']}",
                                "user_id": auth["user"]["id"],
                                "llm_map": True,
                            }
                        )

        payload = json.loads(body.decode("utf-8"))
        self.assertEqual(status, 200)
        self.assertEqual(payload["status"], "success")
        self.assertEqual(payload["report"]["llm_status"], "success")
        self.assertTrue(payload["mapping_path"].endswith("template_mapping.json"))

    def test_handle_draft_template_requires_raw_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = WorkbenchStore(Path(tmp) / "workbench.sqlite3", Path(tmp) / "uploads")
            auth = store.authenticate("demo", "demo123")
            upload = store.store_upload(
                auth["user"]["id"],
                "template.docx",
                "ZG9jeA==",
                content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )

            with patch.object(web_workbench, "STORE", store):
                status, _headers, body = web_workbench.handle_draft_template(
                    {
                        "template_ref": f"upload:{upload['id']}",
                        "raw_input": "   ",
                        "user_id": auth["user"]["id"],
                    }
                )

        self.assertEqual(status, 400)
        self.assertIn("Raw input is required", json.loads(body.decode("utf-8"))["message"])

    def test_handle_draft_template_creates_standalone_run_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_root = root / "agent-runs"
            template = root / "template.docx"
            template.write_bytes(b"fake docx")

            def fake_fill(
                template_path,
                raw_input,
                output_path,
                report_path,
                draft_path,
                style="professional_concise",
                custom_style="",
                existing_content_policy="merge",
            ):
                Path(output_path).write_bytes(b"filled")
                Path(draft_path).write_text('{"drafts": []}', encoding="utf-8")
                report = {
                    "status": "PASS",
                    "filled_fields": [{"template_label": "主要困扰"}],
                    "unfilled_fields": [],
                    "issues": [],
                    "existing_content_policy": existing_content_policy,
                }
                Path(report_path).write_text(json.dumps(report), encoding="utf-8")
                return report

            with patch.object(web_workbench, "RUN_ROOT", run_root):
                with patch.object(web_workbench, "fill_docx_template_from_raw", side_effect=fake_fill):
                    status, _headers, body = web_workbench.handle_draft_template(
                        {
                            "template_path": str(template),
                            "raw_input": "来访者分手后情绪低落。",
                            "style": "warm_clinical",
                            "existing_content_policy": "merge",
                        }
                    )

        payload = json.loads(body.decode("utf-8"))
        self.assertEqual(status, 200)
        self.assertEqual(payload["status"], "success")
        self.assertIn("TEMPLATE", payload["run_dir"])
        self.assertTrue(payload["output_path"].endswith("filled_template.docx"))
        self.assertTrue(payload["draft_path"].endswith("template_draft.json"))
        self.assertEqual(payload["report"]["existing_content_policy"], "merge")

    def test_handle_draft_template_rejects_run_dir_outside_run_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_root = root / "agent-runs"
            run_root.mkdir()
            outside = root / "outside"
            outside.mkdir()
            template = root / "template.docx"
            template.write_bytes(b"fake docx")

            with patch.object(web_workbench, "RUN_ROOT", run_root):
                status, _headers, body = web_workbench.handle_draft_template(
                    {
                        "template_path": str(template),
                        "raw_input": "材料",
                        "run_dir": str(outside),
                    }
                )

        payload = json.loads(body.decode("utf-8"))
        self.assertEqual(status, 400)
        self.assertIn("outside approved output directory", payload["message"])

    def test_handle_draft_template_rejects_template_outside_allowed_roots(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            template = root / "template.docx"
            template.write_bytes(b"fake docx")
            store = WorkbenchStore(root / "workbench.sqlite3", root / "uploads")
            auth = store.authenticate("demo", "demo123")

            with patch.object(web_workbench, "STORE", store):
                status, _headers, body = web_workbench.handle_draft_template(
                    {
                        "template_path": str(template),
                        "raw_input": "鏉愭枡",
                        "user_id": auth["user"]["id"],
                    }
                )

        payload = json.loads(body.decode("utf-8"))
        self.assertEqual(status, 400)
        self.assertIn("approved template directories", payload["message"])

    def test_handle_draft_template_allows_user_uploaded_template(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = WorkbenchStore(root / "workbench.sqlite3", root / "uploads")
            auth = store.authenticate("demo", "demo123")
            upload = store.store_upload(
                auth["user"]["id"],
                "template.docx",
                "ZG9jeA==",
                content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )

            def fake_fill(
                template_path,
                raw_input,
                output_path,
                report_path,
                draft_path,
                style="professional_concise",
                custom_style="",
                existing_content_policy="merge",
            ):
                Path(output_path).write_bytes(b"filled")
                Path(draft_path).write_text('{"drafts": []}', encoding="utf-8")
                report = {"status": "PASS", "filled_fields": [], "unfilled_fields": [], "issues": []}
                Path(report_path).write_text(json.dumps(report), encoding="utf-8")
                return report

            with patch.object(web_workbench, "STORE", store):
                with patch.object(web_workbench, "RUN_ROOT", root / "agent-runs"):
                    with patch.object(web_workbench, "fill_docx_template_from_raw", side_effect=fake_fill):
                        status, _headers, body = web_workbench.handle_draft_template(
                            {
                                "template_ref": f"upload:{upload['id']}",
                                "raw_input": "鏉愭枡",
                                "user_id": auth["user"]["id"],
                            }
                        )

        payload = json.loads(body.decode("utf-8"))
        self.assertEqual(status, 200)
        self.assertEqual(payload["status"], "success")

    def test_handle_inspect_template_returns_slots_and_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            template = Path(tmp) / "template.docx"
            write_test_docx(
                template,
                (
                    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                    f'<w:document xmlns:w="{WORD_NS}">'
                    "<w:body>"
                    "<w:tbl>"
                    "<w:tr>"
                    "<w:tc><w:p><w:r><w:t>主要困扰</w:t></w:r></w:p></w:tc>"
                    "<w:tc><w:p><w:r><w:t>____</w:t></w:r></w:p></w:tc>"
                    "</w:tr>"
                    "<w:tr>"
                    "<w:tc><w:p><w:r><w:t>已有理解</w:t></w:r></w:p></w:tc>"
                    "<w:tc><w:p><w:r><w:t>原有内容</w:t></w:r></w:p></w:tc>"
                    "</w:tr>"
                    "</w:tbl>"
                    "<w:sectPr/>"
                    "</w:body>"
                    "</w:document>"
                ),
            )

            status, _headers, body = web_workbench.handle_inspect_template(
                {"template_path": str(template)}
            )

        payload = json.loads(body.decode("utf-8"))
        self.assertEqual(status, 200)
        self.assertEqual(payload["status"], "success")
        self.assertEqual(payload["summary"]["total_slots"], 2)
        self.assertEqual(payload["summary"]["fillable_slots"], 1)
        self.assertEqual(payload["summary"]["prefilled_slots"], 1)
        self.assertEqual(payload["slots"][0]["label"], "主要困扰")


    def test_handle_demo_catalog_returns_curated_scenarios_and_repo_templates(self):
        with tempfile.TemporaryDirectory() as tmp:
            docs_root = Path(tmp) / "docs"
            docs_root.mkdir()
            template_path = docs_root / "demo-template.docx"
            template_path.write_bytes(b"docx")

            with patch.object(web_workbench, "DOCS_ROOT", docs_root):
                status, _headers, body = web_workbench.handle_demo_catalog()

        payload = json.loads(body.decode("utf-8"))
        self.assertEqual(status, 200)
        self.assertEqual(payload["status"], "success")
        self.assertGreaterEqual(len(payload["scenarios"]), 3)
        self.assertEqual(payload["scenarios"][0]["workflow"], "W2")
        self.assertEqual(payload["templates"][0]["template_ref"], "demo:demo-template")
        self.assertNotIn("path", payload["templates"][0])
        self.assertIn("de-identified", payload["privacy_notice"])
        self.assertTrue(
            any(
                scenario["id"] == "next-session-chinese-session-note-source-material"
                and "会谈记录" in scenario["input"]
                for scenario in payload["scenarios"]
            )
        )

    def test_handle_runs_detail_returns_saved_payload_for_owner(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_root = root / "agent-runs"
            run_dir = run_root / "run-1"
            run_dir.mkdir(parents=True)
            (run_dir / "clean_output.md").write_text("saved output", encoding="utf-8")
            (run_dir / "structured_output.json").write_text('{"workflow":"W3"}', encoding="utf-8")
            (run_dir / "structured_check.json").write_text('{"status":"PASS"}', encoding="utf-8")
            (run_dir / "metadata.json").write_text('{"status":"success"}', encoding="utf-8")
            (run_dir / "output.docx").write_bytes(b"docx")

            store = WorkbenchStore(root / "workbench.sqlite3", root / "uploads")
            auth = store.authenticate("demo", "demo123")
            user = auth["user"]
            store.register_run_artifact(user["id"], str(run_dir), workflow="W3", source_action="workflow.run")

            with patch.object(web_workbench, "STORE", store):
                with patch.object(web_workbench, "RUN_ROOT", run_root):
                    status, _headers, body = web_workbench.handle_runs(
                        user,
                        {"action": "detail", "run_dir": str(run_dir)},
                    )

        payload = json.loads(body.decode("utf-8"))
        self.assertEqual(status, 200)
        self.assertEqual(payload["status"], "success")
        self.assertEqual(payload["workflow"], "W3")
        self.assertEqual(payload["clean_output"], "saved output")
        self.assertEqual(payload["available_files"]["docx"], str((run_dir / "output.docx").resolve()))

    def test_handle_runs_detail_rejects_unregistered_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_root = root / "agent-runs"
            run_dir = run_root / "run-1"
            run_dir.mkdir(parents=True)
            (run_dir / "clean_output.md").write_text("saved output", encoding="utf-8")

            store = WorkbenchStore(root / "workbench.sqlite3", root / "uploads")
            auth = store.authenticate("demo", "demo123")
            user = auth["user"]

            with patch.object(web_workbench, "STORE", store):
                with patch.object(web_workbench, "RUN_ROOT", run_root):
                    status, _headers, body = web_workbench.handle_runs(
                        user,
                        {"action": "detail", "run_dir": str(run_dir)},
                    )

        payload = json.loads(body.decode("utf-8"))
        self.assertEqual(status, 404)
        self.assertEqual(payload["message"], "Run not found.")

    def test_detect_workflow_prefers_w1_for_chinese_first_summary_prompt_that_negates_dap(self):
        details = web_workbench.detect_workflow_details(
            "\u8bf7\u6839\u636e\u9996\u8bbf\u539f\u59cb\u8bb0\u5f55\u6574\u7406\u56fa\u5b9a\u6a21\u677f\u603b\u7ed3\uff0c\u4fdd\u7559\u98ce\u9669\u53d8\u5316\u7ebf\u7d22\uff0c\u4e0d\u8981\u5199\u6210DAP\u6216session note\u3002"
        )

        self.assertEqual(details["workflow"], "W1")
        self.assertEqual(details["w1_mode"], "initial_interview_summary")
        self.assertEqual(details["route_status"], "mixed_signals")
        self.assertEqual(details["top_candidates"][0]["workflow"], "W1")
        self.assertEqual(details["top_candidates"][1]["workflow"], "W3")


if __name__ == "__main__":
    unittest.main()
