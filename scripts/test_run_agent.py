import tempfile
import unittest
import json
import contextlib
import io
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from run_agent import (
    AgentInputError,
    AgentRunError,
    build_prompt_package,
    detect_w1_mode,
    extract_w1_intake_clues,
    extract_structured_json,
    load_rag_chunks,
    load_retrieval_map,
    normalize_structured_output,
    normalize_workflow,
    main,
    parse_args,
    read_user_input,
    run_agent_once,
    selected_chunk_ids_for_workflow,
    strip_agent_marker,
    structured_failure,
    validate_retrieval_coverage,
    validate_structured_output,
)
from run_model_eval import DeepSeekConfig


LOCAL_TIMEZONE = timezone(timedelta(hours=8))


class RunAgentTest(unittest.TestCase):
    def make_rag_fixture(self, tmp_path):
        rag_root = tmp_path / "rag"
        chunk_specs = [
            (
                rag_root / "session-notes" / "risk-change-documentation.md",
                "session-notes-risk-change-documentation-001",
                "session-notes",
                "# Risk change\nKeep risk-change documentation explicit.\n",
            ),
            (
                rag_root / "case-recording" / "professional-materials-recording.md",
                "case-recording-cps-professional-materials-recording-001",
                "case-recording",
                "# Recording\nUse accurate, relevant professional records.\n",
            ),
            (
                rag_root / "ethics-risk" / "risk-boundary.md",
                "ethics-risk-china-risk-boundary-self-harm-harm-to-others-001",
                "ethics-risk",
                "# Risk boundary\nKeep suicide, self-harm, and harm-to-others boundaries explicit.\n",
            ),
        ]
        for chunk_path, chunk_id, rag_section, body in chunk_specs:
            chunk_path.parent.mkdir(parents=True, exist_ok=True)
            chunk_path.write_text(
                (
                    "---\n"
                    f"chunk_id: {chunk_id}\n"
                    f"rag_section: {rag_section}\n"
                    "---\n\n"
                    f"{body}"
                ),
                encoding="utf-8",
            )
        retrieval_map_path = tmp_path / "retrieval-map.json"
        retrieval_map_path.write_text(
            json.dumps(
                {
                    "workflows": {
                        "workflow_3_session_note": {
                            "intent_routes": [
                                {
                                    "intent": "standard session note",
                                    "priority_chunks": [
                                        "session-notes-risk-change-documentation-001",
                                        "case-recording-cps-professional-materials-recording-001",
                                        "ethics-risk-china-risk-boundary-self-harm-harm-to-others-001",
                                    ],
                                }
                            ]
                        }
                    }
                }
            ),
            encoding="utf-8",
        )
        return rag_root, retrieval_map_path

    def make_w1_rag_fixture(self, tmp_path):
        rag_root = tmp_path / "rag"
        chunk_specs = [
            (
                rag_root / "intake-assessment" / "intake-structure.md",
                "intake-assessment-cps-initial-interview-structure-001",
                "intake-assessment",
                "# Intake structure\nUse a bounded initial interview structure.\n",
            ),
            (
                rag_root / "forms-fields" / "intake-fields.md",
                "forms-fields-cps-initial-interview-fields-001",
                "forms-fields",
                "# Intake fields\nKeep intake fields explicit and counselor-facing.\n",
            ),
            (
                rag_root / "ethics-risk" / "risk-boundary.md",
                "ethics-risk-china-risk-boundary-self-harm-harm-to-others-001",
                "ethics-risk",
                "# Risk boundary\nKeep suicide, self-harm, and harm-to-others boundaries explicit.\n",
            ),
            (
                rag_root / "case-recording" / "professional-materials-recording.md",
                "case-recording-cps-professional-materials-recording-001",
                "case-recording",
                "# Recording\nUse accurate, relevant professional records.\n",
            ),
        ]
        for chunk_path, chunk_id, rag_section, body in chunk_specs:
            chunk_path.parent.mkdir(parents=True, exist_ok=True)
            chunk_path.write_text(
                (
                    "---\n"
                    f"chunk_id: {chunk_id}\n"
                    f"rag_section: {rag_section}\n"
                    "---\n\n"
                    f"{body}"
                ),
                encoding="utf-8",
            )
        retrieval_map_path = tmp_path / "retrieval-map.json"
        retrieval_map_path.write_text(
            json.dumps(
                {
                    "workflows": {
                        "workflow_1_intake_form": {
                            "intent_routes": [
                                {
                                    "intent": "initial interview summary",
                                    "priority_chunks": [
                                        "intake-assessment-cps-initial-interview-structure-001",
                                        "forms-fields-cps-initial-interview-fields-001",
                                        "ethics-risk-china-risk-boundary-self-harm-harm-to-others-001",
                                        "case-recording-cps-professional-materials-recording-001",
                                    ],
                                }
                            ]
                        }
                    }
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        return rag_root, retrieval_map_path
        chunk_path = rag_root / "session-notes" / "risk-change-documentation.md"
        chunk_path.parent.mkdir(parents=True)
        chunk_path.write_text(
            "---\nchunk_id: session-notes-risk-change-documentation-001\n---\n\n# 核心规则\n风险变化必须单独列出。\n",
            encoding="utf-8",
        )
        retrieval_map_path = tmp_path / "retrieval-map.json"
        retrieval_map_path.write_text(
            json.dumps(
                {
                    "workflows": {
                        "workflow_3_session_note": {
                            "intent_routes": [
                                {
                                    "intent": "普通 session 记录",
                                    "priority_chunks": [
                                        "session-notes-risk-change-documentation-001"
                                    ],
                                }
                            ]
                        }
                    }
                }
            ),
            encoding="utf-8",
        )
        return rag_root, retrieval_map_path

    def test_normalize_workflow_accepts_aliases(self):
        self.assertEqual(normalize_workflow("W1").workflow_id, "W1")
        self.assertEqual(normalize_workflow("intake").workflow_id, "W1")
        self.assertEqual(normalize_workflow("case").workflow_id, "W2")
        self.assertEqual(normalize_workflow("session").workflow_id, "W3")
        self.assertEqual(normalize_workflow("conceptualization").workflow_id, "W4")
        self.assertEqual(normalize_workflow("next-session-plan").workflow_id, "W5")
        self.assertEqual(normalize_workflow("roadmap").workflow_id, "W6")

    def test_normalize_workflow_rejects_unknown_alias(self):
        with self.assertRaisesRegex(AgentInputError, "W1"):
            normalize_workflow("unknown")

    def test_read_user_input_requires_exactly_one_source(self):
        with self.assertRaisesRegex(AgentInputError, "exactly one"):
            read_user_input(None, None)
        with self.assertRaisesRegex(AgentInputError, "exactly one"):
            read_user_input("inline", "notes.md")

    def test_read_user_input_accepts_inline_text(self):
        source, text = read_user_input("  来访者材料  ", None)

        self.assertEqual(source, "inline")
        self.assertEqual(text, "来访者材料")

    def test_read_user_input_accepts_utf8_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            input_path = Path(tmp) / "notes.md"
            input_path.write_text("  文件材料  ", encoding="utf-8")

            source, text = read_user_input(None, input_path)

        self.assertEqual(source, "file")
        self.assertEqual(text, "文件材料")

    def test_selected_chunk_ids_for_workflow_uses_priority_chunks(self):
        retrieval_map = {
            "workflows": {
                "workflow_3_session_note": {
                    "intent_routes": [
                        {
                            "intent": "普通 session 记录",
                            "priority_chunks": [
                                "session-notes-risk-change-documentation-001",
                                "case-recording-cps-professional-materials-recording-001",
                            ],
                        }
                    ]
                }
            }
        }

        chunk_ids = selected_chunk_ids_for_workflow(
            normalize_workflow("W3"), retrieval_map
        )

        self.assertEqual(
            chunk_ids,
            [
                "session-notes-risk-change-documentation-001",
                "case-recording-cps-professional-materials-recording-001",
            ],
        )

    def test_load_rag_chunks_reads_front_matter_chunk_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            rag_root = Path(tmp) / "rag"
            chunk_path = rag_root / "session-notes" / "risk-change-documentation.md"
            chunk_path.parent.mkdir(parents=True)
            chunk_path.write_text(
                "---\nchunk_id: session-notes-risk-change-documentation-001\n---\n\n# 核心规则\n风险变化必须单独列出。\n",
                encoding="utf-8",
            )

            chunks = load_rag_chunks(
                ["session-notes-risk-change-documentation-001"], rag_root
            )

        self.assertEqual(chunks[0]["chunk_id"], "session-notes-risk-change-documentation-001")
        self.assertIn("风险变化必须单独列出", chunks[0]["content"])

    def test_load_rag_chunks_missing_chunk_raises_before_api(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(AgentRunError, "missing-chunk-001"):
                load_rag_chunks(["missing-chunk-001"], Path(tmp))

    def test_validate_retrieval_coverage_rejects_missing_theory_boundary_chunks(self):
        chunks = [
            {
                "chunk_id": "case-recording-cps-professional-materials-recording-001",
                "path": Path("rag/case-recording/materials-recording.md"),
                "content": (
                    "---\n"
                    "chunk_id: case-recording-cps-professional-materials-recording-001\n"
                    "rag_section: case-recording\n"
                    "---\n"
                    "\n"
                    "# Recording\nUse accurate records.\n"
                ),
            }
        ]

        with self.assertRaisesRegex(AgentRunError, "theory-frameworks.*ethics-risk"):
            validate_retrieval_coverage(normalize_workflow("W4"), chunks)

    def test_run_agent_once_rejects_retrieval_gap_before_model_call(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            rag_root = tmp_path / "rag"
            chunk_path = rag_root / "case-recording" / "materials-recording.md"
            chunk_path.parent.mkdir(parents=True)
            chunk_path.write_text(
                "---\n"
                "chunk_id: case-recording-cps-professional-materials-recording-001\n"
                "rag_section: case-recording\n"
                "---\n"
                "\n"
                "# Recording\nUse accurate records.\n",
                encoding="utf-8",
            )
            retrieval_map_path = tmp_path / "retrieval-map.json"
            retrieval_map_path.write_text(
                json.dumps(
                    {
                        "workflows": {
                            "workflow_4_case_conceptualization": {
                                "intent_routes": [
                                    {
                                        "intent": "broken conceptualization route",
                                        "priority_chunks": [
                                            "case-recording-cps-professional-materials-recording-001"
                                        ],
                                    }
                                ]
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )

            def should_not_call_model(*_args, **_kwargs):
                raise AssertionError("model call should not run when retrieval coverage is invalid")

            with self.assertRaisesRegex(AgentRunError, "theory-frameworks.*ethics-risk"):
                run_agent_once(
                    workflow_value="W4",
                    inline_input="Use a CBT framework to conceptualize this de-identified case.",
                    input_file=None,
                    run_root=tmp_path / "agent-runs",
                    retrieval_map_path=retrieval_map_path,
                    rag_root=rag_root,
                    config=DeepSeekConfig(api_key="key"),
                    http_post_json=should_not_call_model,
                )

    def test_build_prompt_package_includes_context_and_marker(self):
        workflow = normalize_workflow("W3")
        chunks = [
            {
                "chunk_id": "session-notes-risk-change-documentation-001",
                "path": "rag/session-notes/risk-change-documentation.md",
                "content": "# 核心规则\n风险变化必须单独列出。",
            }
        ]

        prompt = build_prompt_package(workflow, "来访者本次谈到很委屈。", chunks)

        self.assertIn("咨询师助理", prompt)
        self.assertIn("Session 总结与咨询记录生成", prompt)
        self.assertIn("session-notes-risk-change-documentation-001", prompt)
        self.assertIn("风险变化必须单独列出", prompt)
        self.assertIn("来访者本次谈到很委屈。", prompt)
        self.assertIn("AGENT_DONE_W3", prompt)

    def test_build_prompt_package_includes_workflow_specific_output_contract(self):
        prompt = build_prompt_package(
            normalize_workflow("W3"),
            "来访者本次谈到很委屈。",
            [
                {
                    "chunk_id": "session-notes-risk-change-documentation-001",
                    "path": "rag/session-notes/risk-change-documentation.md",
                    "content": "# 核心规则\n风险变化必须单独列出。",
                }
            ],
        )

        self.assertIn("本次主题", prompt)
        self.assertIn("来访者状态", prompt)
        self.assertIn("咨询师干预", prompt)
        self.assertIn("风险变化", prompt)
        self.assertIn("下次咨询重点", prompt)

    def test_build_prompt_package_includes_structured_json_contract_when_requested(self):
        prompt = build_prompt_package(
            normalize_workflow("W3"),
            "来访者本次谈到很委屈。",
            [
                {
                    "chunk_id": "session-notes-risk-change-documentation-001",
                    "path": "rag/session-notes/risk-change-documentation.md",
                    "content": "# 核心规则\n风险变化必须单独列出。",
                }
            ],
            structured=True,
        )

        self.assertIn("```json", prompt)
        self.assertIn('"document_type": "session_note"', prompt)
        self.assertIn('"risk_change"', prompt)
        self.assertIn('"boundary_notes"', prompt)
        self.assertIn("本记录不替代咨询师专业判断", prompt)

    def test_build_prompt_package_w4_mentions_framework_hypothesis_boundaries(self):
        prompt = build_prompt_package(
            normalize_workflow("W4"),
            "Please build a CBT case conceptualization for this de-identified case.",
            [
                {
                    "chunk_id": "theory-frameworks-cbt-case-conceptualization-001",
                    "path": "rag/theory-frameworks/cbt-case-conceptualization.md",
                    "content": "# CBT\nUse triggers, beliefs, emotions, behaviors, and maintaining cycles.",
                }
            ],
            structured=True,
        )

        self.assertIn("case conceptualization", prompt.lower())
        self.assertIn('"document_type": "case_conceptualization"', prompt)
        self.assertIn('"selected_framework"', prompt)
        self.assertIn('"working_hypotheses"', prompt)
        self.assertIn('"questions_to_verify"', prompt)
        self.assertIn("AGENT_DONE_W4", prompt)

    def test_build_prompt_package_w5_mentions_single_session_plan_boundaries(self):
        prompt = build_prompt_package(
            normalize_workflow("W5"),
            "Plan the next CBT-oriented counseling session for this de-identified case.",
            [
                {
                    "chunk_id": "next-session-planning-bounded-next-session-plan-001",
                    "path": "rag/next-session-planning/bounded-next-session-plan.md",
                    "content": "# Next-session plan\nKeep the output limited to one upcoming session.",
                }
            ],
            structured=True,
        )

        self.assertIn("next-session plan", prompt.lower())
        self.assertIn('"document_type": "next_session_plan"', prompt)
        self.assertIn('"session_goal"', prompt)
        self.assertIn('"planned_interventions"', prompt)
        self.assertIn('"between_session_tasks"', prompt)
        self.assertIn('"do_not_do"', prompt)
        self.assertIn("AGENT_DONE_W5", prompt)

    def test_build_prompt_package_w6_mentions_bounded_roadmap_contract(self):
        prompt = build_prompt_package(
            normalize_workflow("W6"),
            "Create a bounded CBT counseling roadmap for this de-identified case.",
            [
                {
                    "chunk_id": "roadmap-planning-bounded-counseling-roadmap-001",
                    "path": "rag/roadmap-planning/bounded-counseling-roadmap.md",
                    "content": "# Counseling roadmap\nKeep the output phased, collaborative, and bounded.",
                }
            ],
            structured=True,
        )

        self.assertIn("counseling roadmap", prompt.lower())
        self.assertIn('"document_type": "counseling_roadmap"', prompt)
        self.assertIn('"phases"', prompt)
        self.assertIn('"hypotheses_to_verify"', prompt)
        self.assertIn('"session_focus_options"', prompt)
        self.assertIn('"risk_monitoring_checkpoints"', prompt)
        self.assertIn('"collaboration_referral_reminders"', prompt)
        self.assertIn('"missing_information"', prompt)
        self.assertIn('"do_not_do"', prompt)
        self.assertIn("AGENT_DONE_W6", prompt)

    def test_build_prompt_package_w1_default_contract_is_pre_intake_guide(self):
        prompt = build_prompt_package(
            normalize_workflow("W1"),
            "请生成初访信息收集表",
            [
                {
                    "chunk_id": "forms-fields-pipl-minimum-necessary-fields-001",
                    "path": "rag/forms-fields/pipl-minimum-necessary-fields.md",
                    "content": "# 表单字段规则\n遵循最小必要原则。",
                }
            ],
            structured=True,
        )

        self.assertIn("known_facts", prompt)
        self.assertIn("unclear_or_missing", prompt)
        self.assertIn("follow_up_questions", prompt)
        for label in [
            "初访信息收集表（咨询师访谈辅助版）",
            "咨询目的与个人需求",
            "生物-心理-社会信息",
            "知情同意与边界说明",
            "咨询师初步记录",
        ]:
            self.assertIn(label, prompt)
        self.assertIn("默认任务是帮助咨询师在初访前梳理需要了解的信息和可提问的问题", prompt)
        self.assertIn("不是把用户上传的某个 Word 模板固定成 W1 输出标准", prompt)
        self.assertIn("必须直接使用这些已知信息预填相关栏目", prompt)
        self.assertIn("不要退回成纯空白模板", prompt)
        self.assertNotIn('"title": "心理咨询初始访谈表"', prompt)

    def test_build_prompt_package_w1_uses_partial_case_clues_without_forcing_reask(self):
        prompt = build_prompt_package(
            normalize_workflow("W1"),
            "请生成初访前信息收集表。来访者近两周睡眠变差，偶尔说想消失一下，但没有计划。",
            [
                {
                    "chunk_id": "forms-fields-pipl-minimum-necessary-fields-001",
                    "path": "rag/forms-fields/pipl-minimum-necessary-fields.md",
                    "content": "# 表单字段规则\n遵循最小必要原则。",
                }
            ],
            structured=True,
        )

        self.assertIn("必须直接使用这些已知信息预填相关栏目", prompt)
        self.assertIn("补充其余待核实问题", prompt)
        self.assertIn("不要仅仅要求用户重新提供材料", prompt)

    def test_build_prompt_package_w1_includes_separate_initial_session_summary_mode(self):
        prompt = build_prompt_package(
            normalize_workflow("W1"),
            "这是初始访谈材料，请整理",
            [
                {
                    "chunk_id": "forms-fields-pipl-minimum-necessary-fields-001",
                    "path": "rag/forms-fields/pipl-minimum-necessary-fields.md",
                    "content": "# 表单字段规则\n遵循最小必要原则。",
                }
            ],
            structured=True,
        )

        self.assertIn("W1 初始访谈材料总结模式", prompt)
        self.assertIn("若无法判断用户想要“初访前提问表”还是“已有初访材料总结”，先追问确认", prompt)
        for label in [
            "Main distress",
            "Basic situation",
            "Functioning",
            "Risk and crisis information",
            "Handling suggestions",
            "Other notes",
        ]:
            self.assertIn(label, prompt)

    def test_detect_w1_mode_distinguishes_prep_vs_summary_requests(self):
        self.assertEqual(
            detect_w1_mode("Before tomorrow's first interview, create an intake question guide."),
            "intake_prep",
        )
        self.assertEqual(
            detect_w1_mode(
                "These are completed initial interview notes, not a session record. Organize them into the fixed initial interview summary template."
            ),
            "initial_interview_summary",
        )

    def test_build_prompt_package_w1_summary_includes_section_specific_missing_field_guidance(self):
        prompt = build_prompt_package(
            normalize_workflow("W1"),
            "These are completed initial interview notes, not a session record. Organize them into the fixed initial interview summary template.",
            [
                {
                    "chunk_id": "forms-fields-pipl-minimum-necessary-fields-001",
                    "path": "rag/forms-fields/pipl-minimum-necessary-fields.md",
                    "content": "# Form guidance\nUse the minimum necessary fields only.",
                }
            ],
            structured=True,
        )

        self.assertIn("main_distress", prompt)
        self.assertIn("basic_situation", prompt)
        self.assertIn("risk_crisis", prompt)
        self.assertIn("If a section has no explicit facts", prompt)
        self.assertIn("write at least one concise unclear_or_missing item", prompt)
        self.assertIn("follow_up_questions", prompt)

    def test_extract_w1_intake_clues_captures_partial_known_risk_and_context(self):
        clues = extract_w1_intake_clues(
            "Before tomorrow's first interview, create an intake question guide. "
            "The client has had poor sleep for two weeks because of graduate-school pressure, "
            "more conflict with her roommate, and she sometimes says she wants to disappear, "
            "but there is no plan and she is still attending class."
        )

        self.assertIn("poor sleep for two weeks", clues)
        self.assertIn("graduate-school pressure", clues)
        self.assertIn("conflict with her roommate", clues)
        self.assertIn("wants to disappear", clues)
        self.assertIn("no plan", clues)

    def test_build_prompt_package_w1_prep_includes_known_clue_prefill_guidance(self):
        prompt = build_prompt_package(
            normalize_workflow("W1"),
            "Before tomorrow's first interview, create an intake question guide. "
            "The client has had poor sleep for two weeks because of graduate-school pressure, "
            "more conflict with her roommate, and she sometimes says she wants to disappear, "
            "but there is no plan and she is still attending class.",
            [
                {
                    "chunk_id": "forms-fields-pipl-minimum-necessary-fields-001",
                    "path": "rag/forms-fields/pipl-minimum-necessary-fields.md",
                    "content": "# Form guidance\nUse the minimum necessary fields only.",
                }
            ],
            structured=True,
        )

        self.assertIn("Known intake clues already provided", prompt)
        self.assertIn("poor sleep for two weeks", prompt)
        self.assertIn("graduate-school pressure", prompt)
        self.assertIn("conflict with her roommate", prompt)
        self.assertIn("known_clues_used", prompt)
        self.assertIn("Do not leave the prep guide blank", prompt)

    def test_strip_agent_marker_removes_markdown_wrapped_marker(self):
        clean = strip_agent_marker("正文\n**AGENT_DONE_W3**\n", normalize_workflow("W3"))

        self.assertEqual(clean, "正文\n")

    def test_extract_structured_json_parses_last_fenced_json_block(self):
        workflow = normalize_workflow("W3")
        raw = """
正文
```json
{"workflow": "old"}
```
更多正文
```json
{"workflow": "W3", "document_type": "session_note"}
```
AGENT_DONE_W3
"""

        data, check = extract_structured_json(raw, workflow)

        self.assertEqual(data["workflow"], "W3")
        self.assertEqual(data["document_type"], "session_note")
        self.assertEqual(check["status"], "PASS")

    def test_extract_structured_json_handles_markdown_wrapped_marker(self):
        workflow = normalize_workflow("W3")
        raw = '正文\n```json\n{"workflow": "W3"}\n```\n**AGENT_DONE_W3**\n'

        data, check = extract_structured_json(raw, workflow)

        self.assertEqual(data, {"workflow": "W3"})
        self.assertEqual(check["status"], "PASS")

    def test_extract_structured_json_missing_block_returns_fail_check(self):
        workflow = normalize_workflow("W3")

        data, check = extract_structured_json("正文\nAGENT_DONE_W3\n", workflow)

        self.assertIsNone(data)
        self.assertEqual(check["status"], "FAIL")
        self.assertIn("No fenced JSON block", check["issues"][0]["message"])

    def test_structured_failure_uses_issue_shape(self):
        check = structured_failure(normalize_workflow("W3"), "bad json", path="json")

        self.assertEqual(check["status"], "FAIL")
        self.assertEqual(check["workflow"], "W3")
        self.assertEqual(check["issues"][0]["level"], "ERROR")
        self.assertEqual(check["issues"][0]["path"], "json")

    def helper_validate_structured_output_w1_requires_sensitive_and_risk_fields(self):
        data = {
            "workflow": "W1",
            "document_type": "intake_form",
            "title": "初访信息收集表",
            "sections": [
                {
                    "id": "risk",
                    "heading": "风险评估",
                    "fields": [
                        {
                            "id": "suicide_ideation",
                            "label": "自杀意念",
                            "required": False,
                            "sensitive": True,
                            "risk_signal": True,
                        }
                    ],
                }
            ],
            "boundary_notes": ["本表不构成诊断，需结合咨询师专业判断。"],
        }

        check = validate_structured_output(normalize_workflow("W1"), data)

        self.assertEqual(check["status"], "PASS")

    def helper_validate_structured_output_w1_accepts_pre_intake_guide_sections(self):
        data = {
            "workflow": "W1",
            "document_type": "intake_form",
            "title": "初访信息收集表（咨询师访谈辅助版）",
            "sections": [
                {
                    "heading": "基本信息",
                    "fields": [
                        {
                            "label": "来访者识别信息",
                            "value": "",
                            "required": True,
                            "sensitive": True,
                            "risk_signal": False,
                        }
                    ],
                },
                {
                    "heading": "咨询目的与个人需求",
                    "fields": [
                        {
                            "label": "咨询期待与目标",
                            "value": "",
                            "required": True,
                            "sensitive": False,
                            "risk_signal": False,
                        }
                    ],
                },
                {
                    "heading": "风险评估",
                    "fields": [
                        {
                            "label": "自伤/自杀/他伤及其他安全风险筛查",
                            "value": "",
                            "required": True,
                            "sensitive": True,
                            "risk_signal": True,
                        }
                    ],
                },
            ],
            "boundary_notes": ["本表不构成诊断、最终风险判断或治疗方案。"],
        }

        check = validate_structured_output(normalize_workflow("W1"), data)

        self.assertEqual(check["status"], "PASS")

    def test_validate_structured_output_w1_requires_prefill_trace_when_known_clues_exist(self):
        data = {
            "workflow": "W1",
            "document_type": "intake_form",
            "title": "Initial interview prep guide",
            "known_clues": ["poor sleep for two weeks", "the client says she wants to disappear"],
            "sections": [
                {
                    "heading": "Risk assessment",
                    "fields": [
                        {
                            "label": "Risk screening",
                            "value": "",
                            "suggested_questions": ["Ask about timing, frequency, intent, plan, means, and protective factors."],
                            "known_clues_used": [],
                            "required": True,
                            "sensitive": True,
                            "risk_signal": True,
                        }
                    ],
                }
            ],
            "boundary_notes": ["This is not a diagnosis or final risk rating."],
        }

        check = validate_structured_output(normalize_workflow("W1"), data)

        self.assertEqual(check["status"], "FAIL")
        self.assertTrue(
            any(issue["path"] == "sections.fields.known_clues_used" for issue in check["issues"])
        )

        check = validate_structured_output(normalize_workflow("W1"), data)

        self.assertEqual(check["status"], "FAIL")
        self.assertTrue(
            any(issue["path"] == "sections.fields.known_clues_used" for issue in check["issues"])
        )

    def helper_validate_structured_output_w1_accepts_initial_session_summary_mode(self):
        data = {
            "workflow": "W1",
            "document_type": "initial_session_summary",
            "title": "初始访谈材料总结",
            "sections": [
                {"heading": "来访者主要困扰", "content": "近期情绪低落。"},
                {"heading": "来访者基本情况", "content": "材料中未提供。"},
                {"heading": "危机评估情况", "content": "材料中未提供明确风险信息，建议进一步评估。"},
                {"heading": "处理建议", "content": "下次继续补充评估。"},
            ],
            "boundary_notes": ["仅整理用户已提供材料；不输出最终诊断或最终风险等级。"],
        }

        check = validate_structured_output(normalize_workflow("W1"), data)

        self.assertEqual(check["status"], "PASS")

    def test_validate_structured_output_w1_accepts_initial_session_summary_split_fields(self):
        data = {
            "workflow": "W1",
            "document_type": "initial_session_summary",
            "title": "Initial interview summary",
            "sections": [
                {"id": "main_distress", "heading": "Main distress", "known_facts": ["Recent low mood after a breakup."], "unclear_or_missing": [], "follow_up_questions": ["How long has the low mood been present?"]},
                {"id": "basic_situation", "heading": "Basic situation", "known_facts": [], "unclear_or_missing": ["Family context was not documented."], "follow_up_questions": []},
                {"id": "functioning", "heading": "Functioning", "known_facts": ["Sleep worsened in the last two weeks."], "unclear_or_missing": [], "follow_up_questions": []},
                {"id": "support_coping", "heading": "Support and coping", "known_facts": [], "unclear_or_missing": ["Support system was not yet described."], "follow_up_questions": ["Who does the client usually reach out to for support?"]},
                {"id": "history", "heading": "Prior help-seeking and treatment history", "known_facts": [], "unclear_or_missing": ["Prior counseling history was not provided."], "follow_up_questions": []},
                {"id": "psychological_tests", "heading": "Psychological tests", "known_facts": [], "unclear_or_missing": ["No test results were documented."], "follow_up_questions": []},
                {"id": "risk_crisis", "heading": "Risk and crisis information", "known_facts": ["The notes mention passive disappearance language without a plan."], "unclear_or_missing": ["Access to means and prior attempts were not documented."], "follow_up_questions": ["Ask about self-harm history, intent, plan, means, and protective factors."]},
                {"id": "handling_suggestion", "heading": "Handling suggestions", "known_facts": ["Continue risk clarification and informed-consent review."], "unclear_or_missing": [], "follow_up_questions": []},
                {"id": "other_notes", "heading": "Other notes", "known_facts": [], "unclear_or_missing": ["Some details may reflect counselor shorthand and need confirmation."], "follow_up_questions": []},
            ],
            "summary_guidance": ["Separate known facts, unclear facts, and follow-up questions."],
            "boundary_notes": ["Organize only the provided material and do not output a final diagnosis or risk rating."],
        }

        check = validate_structured_output(normalize_workflow("W1"), data)

        self.assertEqual(check["status"], "PASS")

    def test_validate_structured_output_w1_initial_session_summary_requires_split_fields(self):
        data = {
            "workflow": "W1",
            "document_type": "initial_session_summary",
            "title": "Initial interview summary",
            "sections": [
                {"id": "main_distress", "heading": "Main distress", "content": "Collapsed summary content."}
            ],
            "boundary_notes": ["Working summary only."],
        }

        check = validate_structured_output(normalize_workflow("W1"), data)

        self.assertEqual(check["status"], "FAIL")
        issue_paths = {issue["path"] for issue in check["issues"]}
        self.assertIn("sections[0].known_facts", issue_paths)
        self.assertIn("sections[0].unclear_or_missing", issue_paths)
        self.assertIn("sections[0].follow_up_questions", issue_paths)
        self.assertIn("summary_guidance", issue_paths)

    def test_normalize_structured_output_w1_summary_recovers_sections_from_content_and_aliases(self):
        workflow = normalize_workflow("W1")
        data = {
            "workflow": "W1",
            "document_type": "initial_session_summary",
            "title": "Initial interview summary",
            "sections": [
                {
                    "heading": "Main complaint",
                    "content": "Known facts: Sleep worsened after the breakup.\nMissing: Duration of the low mood was not documented.\nFollow-up: Ask when the sleep change started.",
                },
                {
                    "heading": "风险与危机情况",
                    "content": "Known facts: Notes mention passive disappearance language without a plan.\nMissing: Access to means and prior attempts were not documented.\nFollow-up: Ask about self-harm history, plan, means, and protective factors.",
                },
            ],
            "boundary_notes": ["Organize only provided material."],
        }

        normalized = normalize_structured_output(workflow, data)

        self.assertEqual(normalized["document_type"], "initial_session_summary")
        self.assertEqual(normalized["sections"][0]["id"], "main_distress")
        self.assertEqual(normalized["sections"][0]["known_facts"], ["Sleep worsened after the breakup."])
        self.assertEqual(normalized["sections"][0]["unclear_or_missing"], ["Duration of the low mood was not documented."])
        self.assertEqual(normalized["sections"][0]["follow_up_questions"], ["Ask when the sleep change started."])
        risk_section = next(section for section in normalized["sections"] if section["id"] == "risk_crisis")
        self.assertIn("Notes mention passive disappearance language without a plan.", risk_section["known_facts"])
        self.assertIn("Access to means and prior attempts were not documented.", risk_section["unclear_or_missing"])
        self.assertIn("Ask about self-harm history, plan, means, and protective factors.", risk_section["follow_up_questions"])
        self.assertTrue(normalized["summary_guidance"])

    def test_run_agent_once_structured_w1_summary_normalizes_before_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            rag_root, retrieval_map_path = self.make_w1_rag_fixture(tmp_path)

            def fake_post_json(_url, _headers, _payload, _timeout):
                return {
                    "choices": [
                        {
                            "message": {
                                "content": (
                                    "Initial interview summary\n"
                                    "```json\n"
                                    "{\n"
                                    '  "workflow": "W1",\n'
                                    '  "document_type": "initial_session_summary",\n'
                                    '  "title": "Initial interview summary",\n'
                                    '  "sections": [\n'
                                    '    {"heading": "Main complaint", "content": "Known facts: Sleep worsened after the breakup.\\nMissing: Duration of the low mood was not documented.\\nFollow-up: Ask when the sleep change started."},\n'
                                    '    {"heading": "风险与危机情况", "content": "Known facts: Notes mention passive disappearance language without a plan.\\nMissing: Access to means and prior attempts were not documented.\\nFollow-up: Ask about self-harm history, plan, means, and protective factors."}\n'
                                    "  ],\n"
                                    '  "boundary_notes": ["Organize only provided material."]\n'
                                    "}\n"
                                    "```\n"
                                    "AGENT_DONE_W1\n"
                                )
                            }
                        }
                    ]
                }

            result = run_agent_once(
                workflow_value="W1",
                inline_input="These are completed initial interview notes. Organize them into the fixed initial interview summary template.",
                input_file=None,
                run_root=tmp_path / "agent-runs",
                retrieval_map_path=retrieval_map_path,
                rag_root=rag_root,
                structured=True,
                config=DeepSeekConfig(api_key="secret-key", model="deepseek-test"),
                http_post_json=fake_post_json,
            )

            structured = json.loads((result.run_dir / "structured_output.json").read_text(encoding="utf-8"))
            structured_check = json.loads((result.run_dir / "structured_check.json").read_text(encoding="utf-8"))

        self.assertEqual(structured_check["status"], "PASS")
        self.assertEqual(structured["sections"][0]["id"], "main_distress")
        risk_section = next(section for section in structured["sections"] if section["id"] == "risk_crisis")
        self.assertTrue(risk_section["follow_up_questions"])

    def test_validate_structured_output_w2_requires_core_fields(self):
        data = {
            "workflow": "W2",
            "document_type": "case_summary",
            "title": "个案信息整理",
            "known_facts": ["女性，35岁"],
            "bio_psycho_social": {
                "biological": ["睡眠困难"],
                "psychological": ["委屈"],
                "social": ["夫妻冲突"],
            },
            "risk_signals": ["材料中未见明确风险信号"],
            "information_gaps": ["睡眠持续时间未提供"],
            "suggested_questions": ["睡眠问题持续多久？"],
            "boundary_notes": ["不构成诊断。"],
        }

        check = validate_structured_output(normalize_workflow("W2"), data)

        self.assertEqual(check["status"], "PASS")

    def test_validate_structured_output_w2_allows_empty_risk_signals(self):
        data = {
            "workflow": "W2",
            "document_type": "case_summary",
            "title": "个案信息整理",
            "known_facts": ["女性，35岁"],
            "bio_psycho_social": {
                "biological": ["睡眠困难"],
                "psychological": ["委屈"],
                "social": ["夫妻冲突"],
            },
            "risk_signals": [],
            "information_gaps": ["风险信息需要进一步评估"],
            "suggested_questions": ["最近有没有自伤、自杀或他伤想法？"],
            "boundary_notes": ["材料中未见明确风险信号，建议咨询师按需进一步评估。"],
        }

        check = validate_structured_output(normalize_workflow("W2"), data)

        self.assertEqual(check["status"], "PASS")

    def test_validate_structured_output_w2_accepts_dedicated_bps_background_structure(self):
        data = {
            "workflow": "W2",
            "document_type": "case_summary",
            "title": "Case background organization",
            "presenting_concerns": ["Sleep disruption and marital conflict."],
            "case_overview": {
                "known_facts": ["Adult client, married, one child."],
                "working_hypotheses": ["Stress appears linked to role overload but still needs verification."],
                "information_gaps": ["No clear timeline for symptom escalation."],
            },
            "bio_psycho_social": {
                "biological": {
                    "known_facts": ["Insomnia."],
                    "working_hypotheses": ["Fatigue may be reinforcing irritability."],
                    "information_gaps": ["Sleep duration is not documented."],
                    "follow_up_questions": ["How many hours is the client sleeping most nights?"],
                },
                "psychological": {
                    "known_facts": ["Feels wronged and suppresses emotion before outbursts."],
                    "working_hypotheses": ["Emotion suppression may contribute to abrupt escalation."],
                    "information_gaps": ["No direct description of core beliefs."],
                    "follow_up_questions": ["What thoughts appear before she stops speaking?"],
                },
                "social": {
                    "known_facts": ["Work stress and partner conflict are both active."],
                    "working_hypotheses": ["Limited support at home may worsen distress."],
                    "information_gaps": ["Support network outside the marriage is unclear."],
                    "follow_up_questions": ["Who can provide support outside the home?"],
                },
            },
            "protective_factors": ["Help-seeking and ongoing parenting responsibilities."],
            "risk_formulation": {
                "observed_clues": ["No self-harm or suicide content was reported in the material."],
                "missing_or_unclear": ["Direct risk inquiry results are not documented."],
                "follow_up_questions": ["Ask directly about self-harm, suicide, violence, and alcohol use."],
            },
            "recommended_focus": ["Clarify recent stress timeline and support resources."],
            "boundary_notes": ["This is a counselor-facing case background organizer, not a diagnosis or final risk rating."],
        }

        check = validate_structured_output(normalize_workflow("W2"), data)

        self.assertEqual(check["status"], "PASS")

    def test_validate_structured_output_w2_requires_split_bps_dimensions_and_risk_structure(self):
        data = {
            "workflow": "W2",
            "document_type": "case_summary",
            "title": "Case background organization",
            "presenting_concerns": ["Distress after conflict."],
            "case_overview": {
                "known_facts": ["Adult client."],
                "working_hypotheses": ["May be overwhelmed."],
                "information_gaps": ["History is sparse."],
            },
            "bio_psycho_social": {
                "biological": ["Insomnia"],
                "psychological": {
                    "known_facts": ["Anxiety"],
                    "working_hypotheses": ["Perfectionism may be relevant."],
                    "information_gaps": ["No cognitive details."],
                    "follow_up_questions": ["What thoughts appear before panic?"],
                },
                "social": {
                    "known_facts": ["Family pressure."],
                    "working_hypotheses": ["Support may be inconsistent."],
                    "information_gaps": ["Peer support unknown."],
                    "follow_up_questions": ["Who is available for support?"],
                },
            },
            "protective_factors": ["Help-seeking."],
            "risk_formulation": ["Risk unclear."],
            "recommended_focus": ["Clarify timeline."],
            "boundary_notes": ["Working organizer only."],
        }

        check = validate_structured_output(normalize_workflow("W2"), data)

        self.assertEqual(check["status"], "FAIL")
        issue_paths = {issue["path"] for issue in check["issues"]}
        self.assertIn("bio_psycho_social.biological.known_facts", issue_paths)
        self.assertIn("bio_psycho_social.biological.follow_up_questions", issue_paths)
        self.assertIn("risk_formulation.observed_clues", issue_paths)
        self.assertIn("risk_formulation.follow_up_questions", issue_paths)

    def test_validate_structured_output_w3_requires_stable_sections(self):
        data = {
            "workflow": "W3",
            "document_type": "session_note",
            "title": "本次咨询记录",
            "sections": [
                {"id": "theme", "heading": "本次主题", "content": "..."},
                {"id": "client_status", "heading": "来访者状态", "content": "..."},
                {"id": "intervention", "heading": "咨询师干预", "content": "..."},
                {"id": "risk_change", "heading": "风险变化", "content": "..."},
                {"id": "next", "heading": "下次咨询重点", "content": "..."},
            ],
            "risk_change": {"content": "材料中未提供风险相关信息"},
            "next_session_focus": ["继续讨论表达方式"],
            "missing_information": ["来访者外观信息未提供"],
            "boundary_notes": ["本记录不替代咨询师专业判断。"],
        }

        check = validate_structured_output(normalize_workflow("W3"), data)

        self.assertEqual(check["status"], "PASS")

    def test_validate_structured_output_forbidden_diagnosis_terms_fail(self):
        data = {
            "workflow": "W3",
            "document_type": "session_note",
            "title": "本次咨询记录",
            "sections": [
                {"heading": "本次主题", "content": "确诊为抑郁症"},
                {"heading": "来访者状态", "content": "..."},
                {"heading": "咨询师干预", "content": "..."},
                {"heading": "风险变化", "content": "..."},
                {"heading": "下次咨询重点", "content": "..."},
            ],
            "risk_change": {},
            "next_session_focus": [],
            "missing_information": [],
            "boundary_notes": ["本记录不替代咨询师专业判断。"],
        }

        check = validate_structured_output(normalize_workflow("W3"), data)

        self.assertEqual(check["status"], "FAIL")
        self.assertTrue(any("确诊为" in issue["message"] for issue in check["issues"]))

    def test_validate_structured_output_w3_accepts_dap_record_with_risk_change_fields(self):
        data = {
            "workflow": "W3",
            "document_type": "session_note",
            "title": "DAP counseling record",
            "record_format": "DAP",
            "sections": [
                {"id": "data", "heading": "Data", "content": "Client reported less anxiety this week but still feared making mistakes in a work presentation."},
                {"id": "assessment", "heading": "Assessment", "content": "Performance-threat thinking may still be active even though acute distress appears somewhat lower."},
                {"id": "plan", "heading": "Plan", "content": "Review coping rehearsal, monitor anxiety around the next presentation, and revisit follow-through."},
                {"id": "risk_change", "heading": "Risk change", "content": "No new self-harm or suicide escalation was documented in the source note."},
            ],
            "risk_change": {
                "content": "No new self-harm or suicide escalation was documented in the source note.",
                "change_documentation": ["Compared with the prior session, the material does not describe a new escalation in self-harm, suicide, violence, or substance risk."],
                "follow_up_actions": ["Re-check ideation, access to means, and environmental safety if concern rises or the history is unclear."],
            },
            "next_session_focus": ["Review the presentation outcome and coping follow-through."],
            "missing_information": ["No direct counselor observation was documented in the source note."],
            "boundary_notes": ["This is a counselor-facing record, not a diagnosis or final risk judgment."],
        }

        check = validate_structured_output(normalize_workflow("W3"), data)

        self.assertEqual(check["status"], "PASS")

    def test_validate_structured_output_w3_requires_risk_change_documentation_lists(self):
        data = {
            "workflow": "W3",
            "document_type": "session_note",
            "title": "Incomplete session note",
            "record_format": "SOAP",
            "sections": [
                {"id": "subjective", "heading": "S", "content": "Client reported lower anxiety."},
                {"id": "objective", "heading": "O", "content": "The source material does not include counselor observation details."},
                {"id": "assessment", "heading": "A", "content": "Anxiety may still be linked to performance concerns."},
                {"id": "plan", "heading": "P", "content": "Review coping rehearsal next time."},
                {"id": "risk_change", "heading": "Risk change", "content": "No new risk material provided."},
            ],
            "risk_change": {"content": "No new risk material provided."},
            "next_session_focus": ["Review coping follow-through."],
            "missing_information": ["No direct counselor observation was documented."],
            "boundary_notes": ["This is a counselor-facing record, not a diagnosis or final risk judgment."],
        }

        check = validate_structured_output(normalize_workflow("W3"), data)

        self.assertEqual(check["status"], "FAIL")
        issue_paths = {issue["path"] for issue in check["issues"]}
        self.assertIn("risk_change.change_documentation", issue_paths)
        self.assertIn("risk_change.follow_up_actions", issue_paths)

    def test_validate_structured_output_w4_accepts_framework_specific_conceptualization(self):
        data = {
            "workflow": "W4",
            "document_type": "case_conceptualization",
            "title": "CBT case conceptualization",
            "selected_framework": "CBT",
            "known_facts": ["Sleep worsened after conflict with father."],
            "presenting_patterns": ["Avoids conflict and ruminates afterward."],
            "predisposing_factors": ["Long-standing sensitivity to criticism is possible but still needs verification."],
            "precipitating_factors": ["Recent family pressure and job stress."],
            "maintaining_factors": ["Rumination and avoidance may reinforce distress."],
            "protective_factors": ["Help-seeking and continued work attendance."],
            "risk_considerations": ["Passive suicide-related wording was reported; further assessment is needed."],
            "working_hypotheses": ["The case may involve a criticism-threat cycle shaped by perfectionistic beliefs."],
            "questions_to_verify": ["What automatic thoughts appear before withdrawal?"],
            "boundary_notes": ["This is a working hypothesis, not a diagnosis or final treatment decision."],
        }

        check = validate_structured_output(normalize_workflow("W4"), data)

        self.assertEqual(check["status"], "PASS")

    def test_validate_structured_output_w4_requires_framework_and_hypotheses(self):
        data = {
            "workflow": "W4",
            "document_type": "case_conceptualization",
            "title": "Missing framework",
            "known_facts": ["Known fact"],
            "boundary_notes": ["Working hypothesis only."],
        }

        check = validate_structured_output(normalize_workflow("W4"), data)

        self.assertEqual(check["status"], "FAIL")
        issue_paths = {issue["path"] for issue in check["issues"]}
        self.assertIn("selected_framework", issue_paths)
        self.assertIn("working_hypotheses", issue_paths)

    def test_validate_structured_output_w5_requires_plan_sections(self):
        data = {
            "workflow": "W5",
            "document_type": "next_session_plan",
            "title": "Next session plan",
            "selected_framework": "cbt",
            "boundary_notes": ["Single-session plan only."],
        }

        check = validate_structured_output(normalize_workflow("W5"), data)

        self.assertEqual(check["status"], "FAIL")
        issue_paths = {issue["path"] for issue in check["issues"]}
        self.assertIn("session_goal", issue_paths)
        self.assertIn("planned_interventions", issue_paths)
        self.assertIn("between_session_tasks", issue_paths)
        self.assertIn("do_not_do", issue_paths)

    def test_validate_structured_output_w5_accepts_bounded_plan(self):
        data = {
            "workflow": "W5",
            "document_type": "next_session_plan",
            "title": "Next session plan",
            "selected_framework": "cbt",
            "session_goal": "Help the counselor explore the criticism-anxiety cycle.",
            "focus_areas": ["Review the trigger-thought-emotion sequence before performance reviews."],
            "planned_interventions": ["Use a brief thought record in session to test the client's feared prediction."],
            "suggested_questions": ["What happens in the first minute after receiving criticism?"],
            "risk_monitoring": ["Re-check suicide ideation, self-harm, and sleep deterioration at the start of session."],
            "between_session_tasks": ["Invite the client to jot down one recent criticism episode if appropriate."],
            "do_not_do": ["Do not turn this into a full treatment roadmap or assign unsafe exposure work."],
            "boundary_notes": ["This is a single-session working plan, not a diagnosis or full treatment plan."],
        }

        check = validate_structured_output(normalize_workflow("W5"), data)

        self.assertEqual(check["status"], "PASS")

    def test_validate_structured_output_w6_requires_roadmap_sections(self):
        data = {
            "workflow": "W6",
            "document_type": "counseling_roadmap",
            "title": "Counseling roadmap",
            "selected_framework": "cbt",
            "boundary_notes": ["This is a bounded roadmap, not a diagnosis or rigid treatment prescription."],
        }

        check = validate_structured_output(normalize_workflow("W6"), data)

        self.assertEqual(check["status"], "FAIL")
        issue_paths = {issue["path"] for issue in check["issues"]}
        self.assertIn("overview", issue_paths)
        self.assertIn("phases", issue_paths)
        self.assertIn("hypotheses_to_verify", issue_paths)
        self.assertIn("session_focus_options", issue_paths)
        self.assertIn("risk_monitoring_checkpoints", issue_paths)
        self.assertIn("collaboration_referral_reminders", issue_paths)
        self.assertIn("missing_information", issue_paths)
        self.assertIn("do_not_do", issue_paths)

    def test_validate_structured_output_w6_accepts_bounded_roadmap(self):
        data = {
            "workflow": "W6",
            "document_type": "counseling_roadmap",
            "title": "Counseling roadmap",
            "selected_framework": "cbt",
            "overview": "Use a phased roadmap to test the criticism-anxiety-avoidance cycle without promising a fixed treatment course.",
            "phases": [
                {
                    "phase_name": "Early engagement and stabilization",
                    "goals": ["Clarify goals and map the criticism-anxiety-avoidance pattern."],
                    "markers_to_monitor": ["Sleep disruption", "avoidance after criticism", "risk language"],
                }
            ],
            "hypotheses_to_verify": ["Harsh self-appraisal may intensify avoidance after supervisor feedback."],
            "session_focus_options": ["Review one recent criticism episode and identify automatic thoughts."],
            "risk_monitoring_checkpoints": ["Revisit suicide ideation, self-harm, and escalation in withdrawal at phase transitions."],
            "collaboration_referral_reminders": ["Consider referral discussion only if new safety, psychiatric, or medical concerns emerge and according to counselor judgment."],
            "missing_information": ["History of prior counseling responses is not yet documented."],
            "do_not_do": ["Do not treat this as a diagnosis, guaranteed timeline, or rigid treatment prescription."],
            "boundary_notes": ["This roadmap is a working aid for counselor planning and must be revised with ongoing assessment."],
        }

        check = validate_structured_output(normalize_workflow("W6"), data)

        self.assertEqual(check["status"], "PASS")

    def test_load_retrieval_map_reads_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "retrieval-map.json"
            path.write_text('{"workflows": {}}', encoding="utf-8")

            loaded = load_retrieval_map(path)

        self.assertEqual(loaded, {"workflows": {}})

    def test_run_agent_once_dry_run_persists_prompt_package(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            rag_root, retrieval_map_path = self.make_rag_fixture(tmp_path)
            run_root = tmp_path / "agent-runs"

            result = run_agent_once(
                workflow_value="W3",
                inline_input="来访者本次谈到很委屈。",
                input_file=None,
                run_root=run_root,
                retrieval_map_path=retrieval_map_path,
                rag_root=rag_root,
                dry_run=True,
                now=datetime(2026, 6, 9, 14, 30, 12, tzinfo=LOCAL_TIMEZONE),
            )

            input_data = json.loads((result.run_dir / "input.json").read_text(encoding="utf-8"))
            metadata = json.loads((result.run_dir / "metadata.json").read_text(encoding="utf-8"))
            prompt = (result.run_dir / "prompt_package.txt").read_text(encoding="utf-8")

        self.assertEqual(result.status, "dry_run")
        self.assertEqual(result.run_dir.name, "2026-06-09-143012-W3")
        self.assertEqual(input_data["workflow"], "W3")
        self.assertEqual(input_data["input_source"], "inline")
        self.assertEqual(metadata["status"], "dry_run")
        self.assertEqual(
            metadata["selected_rag_chunks"],
            [
                "session-notes-risk-change-documentation-001",
                "case-recording-cps-professional-materials-recording-001",
                "ethics-risk-china-risk-boundary-self-harm-harm-to-others-001",
            ],
        )
        self.assertIn("来访者本次谈到很委屈。", prompt)

    def test_run_agent_once_structured_dry_run_adds_prompt_contract_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            rag_root, retrieval_map_path = self.make_rag_fixture(tmp_path)

            result = run_agent_once(
                workflow_value="W3",
                inline_input="来访者本次谈到很委屈。",
                input_file=None,
                run_root=tmp_path / "agent-runs",
                retrieval_map_path=retrieval_map_path,
                rag_root=rag_root,
                dry_run=True,
                structured=True,
            )

            prompt = (result.run_dir / "prompt_package.txt").read_text(encoding="utf-8")

        self.assertIn("```json", prompt)
        self.assertFalse((result.run_dir / "structured_output.json").exists())
        self.assertFalse((result.run_dir / "structured_check.json").exists())

    def test_run_agent_once_api_success_writes_clean_output_and_safety_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            rag_root, retrieval_map_path = self.make_rag_fixture(tmp_path)
            run_root = tmp_path / "agent-runs"
            calls = []

            def fake_post_json(url, headers, payload, timeout):
                calls.append((url, headers, payload, timeout))
                return {
                    "choices": [
                        {
                            "message": {
                                "content": (
                                    "本次咨询记录\n"
                                    "本次主题\n"
                                    "来访者状态\n"
                                    "咨询师干预\n"
                                    "风险变化\n"
                                    "材料中未提供风险相关信息，建议咨询师按需进一步评估。\n"
                                    "下次咨询重点\n"
                                    "咨询记录\n"
                                    "AGENT_DONE_W3\n"
                                )
                            },
                            "finish_reason": "stop",
                        }
                    ],
                    "usage": {"total_tokens": 123},
                }

            result = run_agent_once(
                workflow_value="W3",
                inline_input="来访者本次谈到很委屈。",
                input_file=None,
                run_root=run_root,
                retrieval_map_path=retrieval_map_path,
                rag_root=rag_root,
                dry_run=False,
                config=DeepSeekConfig(api_key="secret-key", model="deepseek-test"),
                http_post_json=fake_post_json,
                now=datetime(2026, 6, 9, 14, 30, 12, tzinfo=LOCAL_TIMEZONE),
            )

            raw_output = (result.run_dir / "raw_output.txt").read_text(encoding="utf-8")
            clean_output = (result.run_dir / "clean_output.md").read_text(encoding="utf-8")
            metadata = json.loads((result.run_dir / "metadata.json").read_text(encoding="utf-8"))
            safety = json.loads((result.run_dir / "safety_check.json").read_text(encoding="utf-8"))

        self.assertEqual(result.status, "success")
        self.assertEqual(calls[0][2]["model"], "deepseek-test")
        self.assertIn("AGENT_DONE_W3", raw_output)
        self.assertNotIn("AGENT_DONE_W3", clean_output)
        self.assertEqual(metadata["status"], "success")
        self.assertEqual(metadata["usage"], {"total_tokens": 123})
        self.assertEqual(safety["rubric_status"], "PASS")

    def test_run_agent_once_structured_api_success_writes_structured_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            rag_root, retrieval_map_path = self.make_rag_fixture(tmp_path)

            def fake_post_json(_url, _headers, _payload, _timeout):
                self.assertEqual(_payload["max_tokens"], 8192)
                return {
                    "choices": [
                        {
                            "message": {
                                "content": (
                                    "本次咨询记录\n"
                                    "本次主题\n来访者状态\n咨询师干预\n风险变化\n"
                                    "材料中未提供风险相关信息，建议咨询师按需进一步评估。\n"
                                    "下次咨询重点\n咨询记录\n"
                                    "```json\n"
                                    "{\n"
                                    '  "workflow": "W3",\n'
                                    '  "document_type": "session_note",\n'
                                    '  "title": "本次咨询记录",\n'
                                    '  "sections": [\n'
                                    '    {"heading": "本次主题", "content": "主题"},\n'
                                    '    {"heading": "来访者状态", "content": "未提供"},\n'
                                    '    {"heading": "咨询师干预", "content": "回顾关键片段"},\n'
                                    '    {"heading": "风险变化", "content": "材料中未提供风险相关信息"},\n'
                                    '    {"heading": "下次咨询重点", "content": "表达方式"}\n'
                                    "  ],\n"
                                    '  "risk_change": {"content": "材料中未提供风险相关信息"},\n'
                                    '  "next_session_focus": ["继续讨论表达方式"],\n'
                                    '  "missing_information": ["来访者状态未提供"],\n'
                                    '  "boundary_notes": ["本记录不替代咨询师专业判断。"]\n'
                                    "}\n"
                                    "```\n"
                                    "AGENT_DONE_W3\n"
                                )
                            }
                        }
                    ]
                }

            result = run_agent_once(
                workflow_value="W3",
                inline_input="来访者本次谈到很委屈。",
                input_file=None,
                run_root=tmp_path / "agent-runs",
                retrieval_map_path=retrieval_map_path,
                rag_root=rag_root,
                dry_run=False,
                structured=True,
                config=DeepSeekConfig(api_key="secret-key", model="deepseek-test"),
                http_post_json=fake_post_json,
            )

            structured = json.loads((result.run_dir / "structured_output.json").read_text(encoding="utf-8"))
            structured_check = json.loads((result.run_dir / "structured_check.json").read_text(encoding="utf-8"))
            metadata = json.loads((result.run_dir / "metadata.json").read_text(encoding="utf-8"))

        self.assertEqual(structured["workflow"], "W3")
        self.assertEqual(structured_check["status"], "PASS")
        self.assertEqual(metadata["structured_status"], "PASS")

    def test_run_agent_once_docx_writes_output_docx_and_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            rag_root, retrieval_map_path = self.make_rag_fixture(tmp_path)

            def fake_post_json(_url, _headers, _payload, _timeout):
                return {
                    "choices": [
                        {
                            "message": {
                                "content": (
                                    "本次咨询记录\n"
                                    "本次主题\n来访者状态\n咨询师干预\n风险变化\n"
                                    "材料中未提供风险相关信息，建议咨询师按需进一步评估。\n"
                                    "下次咨询重点\n咨询记录\n"
                                    "```json\n"
                                    "{\n"
                                    '  "workflow": "W3",\n'
                                    '  "document_type": "session_note",\n'
                                    '  "title": "本次咨询记录",\n'
                                    '  "sections": [\n'
                                    '    {"heading": "本次主题", "content": "主题"},\n'
                                    '    {"heading": "来访者状态", "content": "未提供"},\n'
                                    '    {"heading": "咨询师干预", "content": "回顾关键片段"},\n'
                                    '    {"heading": "风险变化", "content": "材料中未提供风险相关信息"},\n'
                                    '    {"heading": "下次咨询重点", "content": "表达方式"}\n'
                                    "  ],\n"
                                    '  "risk_change": {"content": "材料中未提供风险相关信息"},\n'
                                    '  "next_session_focus": ["继续讨论表达方式"],\n'
                                    '  "missing_information": ["来访者状态未提供"],\n'
                                    '  "boundary_notes": ["本记录不替代咨询师专业判断。"]\n'
                                    "}\n"
                                    "```\n"
                                    "AGENT_DONE_W3\n"
                                )
                            }
                        }
                    ]
                }

            result = run_agent_once(
                workflow_value="W3",
                inline_input="来访者本次谈到很委屈。",
                input_file=None,
                run_root=tmp_path / "agent-runs",
                retrieval_map_path=retrieval_map_path,
                rag_root=rag_root,
                docx=True,
                config=DeepSeekConfig(api_key="secret-key", model="deepseek-test"),
                http_post_json=fake_post_json,
            )

            metadata = json.loads((result.run_dir / "metadata.json").read_text(encoding="utf-8"))
            docx_check = json.loads((result.run_dir / "docx_check.json").read_text(encoding="utf-8"))
            output_exists = (result.run_dir / "output.docx").exists()

        self.assertTrue(output_exists)
        self.assertEqual(docx_check["status"], "PASS")
        self.assertEqual(metadata["docx_status"], "PASS")

    def test_run_agent_once_docx_skips_output_when_structured_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            rag_root, retrieval_map_path = self.make_rag_fixture(tmp_path)

            def fake_post_json(_url, _headers, _payload, _timeout):
                return {
                    "choices": [
                        {
                            "message": {
                                "content": "正文\n```json\n{\"workflow\":\"W3\"}\n```\nAGENT_DONE_W3\n"
                            }
                        }
                    ]
                }

            result = run_agent_once(
                workflow_value="W3",
                inline_input="来访者本次谈到很委屈。",
                input_file=None,
                run_root=tmp_path / "agent-runs",
                retrieval_map_path=retrieval_map_path,
                rag_root=rag_root,
                docx=True,
                config=DeepSeekConfig(api_key="secret-key", model="deepseek-test"),
                http_post_json=fake_post_json,
            )

            docx_check = json.loads((result.run_dir / "docx_check.json").read_text(encoding="utf-8"))

        self.assertFalse((result.run_dir / "output.docx").exists())
        self.assertEqual(docx_check["status"], "FAIL")

    def test_run_agent_once_structured_validation_failure_writes_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            rag_root, retrieval_map_path = self.make_rag_fixture(tmp_path)

            def fake_post_json(_url, _headers, _payload, _timeout):
                return {
                    "choices": [
                        {
                            "message": {
                                "content": (
                                    "正文\n"
                                    "```json\n"
                                    '{"workflow":"W3","document_type":"session_note","title":"bad"}'
                                    "\n```\nAGENT_DONE_W3\n"
                                )
                            }
                        }
                    ]
                }

            result = run_agent_once(
                workflow_value="W3",
                inline_input="来访者本次谈到很委屈。",
                input_file=None,
                run_root=tmp_path / "agent-runs",
                retrieval_map_path=retrieval_map_path,
                rag_root=rag_root,
                structured=True,
                config=DeepSeekConfig(api_key="secret-key", model="deepseek-test"),
                http_post_json=fake_post_json,
            )

            structured_check = json.loads((result.run_dir / "structured_check.json").read_text(encoding="utf-8"))
            metadata = json.loads((result.run_dir / "metadata.json").read_text(encoding="utf-8"))

        self.assertEqual(structured_check["status"], "FAIL")
        self.assertEqual(metadata["structured_status"], "FAIL")

    def test_run_agent_once_api_error_redacts_key_and_skips_raw_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            rag_root, retrieval_map_path = self.make_rag_fixture(tmp_path)

            def fake_post_json(_url, _headers, _payload, _timeout):
                raise RuntimeError("boom secret-key")

            result = run_agent_once(
                workflow_value="W3",
                inline_input="来访者本次谈到很委屈。",
                input_file=None,
                run_root=tmp_path / "agent-runs",
                retrieval_map_path=retrieval_map_path,
                rag_root=rag_root,
                dry_run=False,
                config=DeepSeekConfig(api_key="secret-key", model="deepseek-test"),
                http_post_json=fake_post_json,
            )

            metadata_text = (result.run_dir / "metadata.json").read_text(encoding="utf-8")
            metadata = json.loads(metadata_text)

        self.assertEqual(result.status, "error")
        self.assertEqual(metadata["status"], "error")
        self.assertEqual(metadata["error_type"], "api_error")
        self.assertIn("[REDACTED]", metadata_text)
        self.assertNotIn("secret-key", metadata_text)
        self.assertFalse((result.run_dir / "raw_output.txt").exists())

    def test_parse_args_accepts_dry_run_command(self):
        args = parse_args(["--workflow", "W3", "--input", "text", "--dry-run"])

        self.assertEqual(args.workflow, "W3")
        self.assertEqual(args.input, "text")
        self.assertTrue(args.dry_run)

    def test_parse_args_accepts_structured_flag(self):
        args = parse_args(["--workflow", "W3", "--input", "text", "--structured"])

        self.assertTrue(args.structured)

    def test_parse_args_accepts_docx_flag(self):
        args = parse_args(["--workflow", "W3", "--input", "text", "--docx"])

        self.assertTrue(args.docx)

    def test_main_returns_nonzero_for_unknown_workflow(self):
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            code = main(["--workflow", "nope", "--input", "text", "--dry-run"])

        self.assertEqual(code, 2)
        self.assertIn("Accepted workflows", stderr.getvalue())

    def test_main_prints_run_dir_on_success(self):
        stdout = io.StringIO()

        class Result:
            workflow_id = "W3"
            status = "dry_run"
            run_dir = Path("agent-runs/fake-W3")

        with patch("run_agent.run_agent_once", return_value=Result()):
            with contextlib.redirect_stdout(stdout):
                code = main(["--workflow", "W3", "--input", "text", "--dry-run"])

        self.assertEqual(code, 0)
        self.assertIn("agent-runs", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
