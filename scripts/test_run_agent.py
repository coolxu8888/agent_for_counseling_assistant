import tempfile
import unittest
import json
from datetime import datetime, timezone
from pathlib import Path

from run_agent import (
    AgentInputError,
    AgentRunError,
    build_prompt_package,
    load_rag_chunks,
    load_retrieval_map,
    normalize_workflow,
    read_user_input,
    run_agent_once,
    selected_chunk_ids_for_workflow,
)
from run_model_eval import DeepSeekConfig


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
                now=datetime(2026, 6, 9, 14, 30, 12, tzinfo=timezone.utc),
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
                now=datetime(2026, 6, 9, 14, 30, 12, tzinfo=timezone.utc),
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


if __name__ == "__main__":
    unittest.main()
