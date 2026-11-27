import json
import tempfile
import unittest
from pathlib import Path

import test_run_agent
from run_agent import AgentInputError, W1_INITIAL_SESSION_SUMMARY_CONTRACT, run_agent_once
from run_model_eval import DeepSeekConfig


def intake_response():
    data = {
        "workflow": "W1",
        "document_type": "intake_form",
        "title": "Synthetic intake preparation",
        "sections": [{
            "id": "risk",
            "heading": "Safety check",
            "fields": [{
                "id": "safety",
                "label": "Safety",
                "required": True,
                "sensitive": True,
                "risk_signal": True,
                "suggested_questions": ["What would help you feel comfortable speaking today?"],
            }],
        }],
        "boundary_notes": ["Discuss consent and confidentiality."],
    }
    return "```json\n" + json.dumps(data) + "\n```\nAGENT_DONE_W1\n"


class IntakeGenerationBudgetTest(unittest.TestCase):
    def run_intake(self, content, finish_reason, config, **kwargs):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        rag_root, retrieval_map_path = test_run_agent.RunAgentTest().make_w1_rag_fixture(root)
        calls = []

        def post_response(_url, _headers, payload, _timeout):
            calls.append(payload)
            return {
                "choices": [{"message": {"content": content}, "finish_reason": finish_reason}],
                "usage": {"total_tokens": 40},
            }

        result = run_agent_once(
            "W1",
            inline_input="Prepare a pre-interview intake form.",
            run_root=root / "runs",
            retrieval_map_path=retrieval_map_path,
            rag_root=rag_root,
            config=config,
            http_post_json=post_response,
            docx=True,
            **kwargs,
        )
        metadata = json.loads((result.run_dir / "metadata.json").read_text(encoding="utf-8"))
        return result, metadata, calls

    def test_default_budget_and_valid_json_only_response(self):
        result, metadata, calls = self.run_intake(
            intake_response(), "stop", DeepSeekConfig(api_key="test-key"),
        )
        self.assertEqual(result.status, "success")
        self.assertTrue((result.run_dir / "output.docx").is_file())
        self.assertEqual((result.run_dir / "clean_output.md").read_text(encoding="utf-8").strip(), "")
        self.assertEqual(calls[0]["max_tokens"], 32768)
        self.assertEqual(metadata["max_tokens"], 32768)

    def test_model_override_preserves_configured_generation_budget(self):
        result, metadata, calls = self.run_intake(
            intake_response(), "stop",
            DeepSeekConfig(api_key="test-key", max_output_tokens=65536),
            model_override="test-override",
        )
        self.assertEqual(result.status, "success")
        self.assertEqual(calls[0]["model"], "test-override")
        self.assertEqual(calls[0]["max_tokens"], 65536)
        self.assertEqual(metadata["max_tokens"], 65536)

    def test_length_response_retains_diagnostics_and_never_exports_or_retries(self):
        for content in (intake_response(), None):
            with self.subTest(has_content=content is not None):
                result, metadata, calls = self.run_intake(
                    content, "length", DeepSeekConfig(api_key="test-key"),
                )
                self.assertEqual(result.status, "error")
                self.assertEqual(metadata["status"], "error")
                self.assertEqual(metadata["finish_reason"], "length")
                self.assertEqual(metadata["max_tokens"], 32768)
                self.assertEqual(metadata["usage"], {"total_tokens": 40})
                self.assertEqual(len(calls), 1)
                self.assertTrue((result.run_dir / "raw_output.txt").is_file())
                for filename in ("clean_output.md", "structured_output.json", "output.docx"):
                    self.assertFalse((result.run_dir / filename).exists())

    def test_empty_or_unparseable_intake_body_is_an_error(self):
        for content in ("AGENT_DONE_W1\n", "Partial\n```json\n{", "```json\nnull\n```"):
            with self.subTest(content=content):
                result, metadata, _calls = self.run_intake(
                    content, None, DeepSeekConfig(api_key="test-key"),
                )
                self.assertEqual(result.status, "error")
                self.assertEqual(metadata["status"], "error")
                for filename in ("clean_output.md", "structured_output.json", "output.docx"):
                    self.assertFalse((result.run_dir / filename).exists())

    def test_preparation_rejects_a_completed_interview_summary(self):
        summary = "```json\n" + json.dumps(W1_INITIAL_SESSION_SUMMARY_CONTRACT) + "\n```\nAGENT_DONE_W1\n"
        result, metadata, _calls = self.run_intake(summary, "stop", DeepSeekConfig(api_key="test-key"))
        self.assertEqual(result.status, "error")
        self.assertEqual(metadata["structured_status"], "FAIL")
        self.assertFalse((result.run_dir / "structured_output.json").exists())
        self.assertFalse((result.run_dir / "output.docx").exists())

    def test_existing_word_is_preserved_when_an_explicit_run_directory_is_reused(self):
        with tempfile.TemporaryDirectory() as directory:
            run_dir = Path(directory)
            previous_word = run_dir / "output.docx"
            previous_word.write_bytes(b"previous output")
            with self.assertRaisesRegex(AgentInputError, "already contains"):
                self.run_intake(
                    intake_response(), "length", DeepSeekConfig(api_key="test-key"), run_dir=run_dir,
                )
            self.assertEqual(previous_word.read_bytes(), b"previous output")
            self.assertFalse((run_dir / "metadata.json").exists())


if __name__ == "__main__":
    unittest.main()
