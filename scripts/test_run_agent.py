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
    extract_structured_json,
    load_rag_chunks,
    load_retrieval_map,
    normalize_workflow,
    main,
    parse_args,
    read_user_input,
    run_agent_once,
    selected_chunk_ids_for_workflow,
    strip_agent_marker,
    structured_failure,
    validate_structured_output,
)
from run_model_eval import DeepSeekConfig


LOCAL_TIMEZONE = timezone(timedelta(hours=8))


class RunAgentTest(unittest.TestCase):
    def make_rag_fixture(self, tmp_path):
        rag_root = tmp_path / "rag"
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

    def test_validate_structured_output_w1_requires_sensitive_and_risk_fields(self):
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
            ["session-notes-risk-change-documentation-001"],
        )
        self.assertIn("来访者本次谈到很委屈。", prompt)

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
