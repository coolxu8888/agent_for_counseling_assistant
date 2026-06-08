import tempfile
import unittest
from pathlib import Path

from run_agent import (
    AgentInputError,
    AgentRunError,
    build_prompt_package,
    load_rag_chunks,
    load_retrieval_map,
    normalize_workflow,
    read_user_input,
    selected_chunk_ids_for_workflow,
)


class RunAgentTest(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
