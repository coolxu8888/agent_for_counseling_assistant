import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import build_workflow_eval_prompts


class BuildWorkflowEvalPromptsTest(unittest.TestCase):
    def test_evals_include_w5_next_session_plan(self):
        w5 = next(
            item for item in build_workflow_eval_prompts.EVALS if item["id"] == "W5-001"
        )

        self.assertIn("next-session plan", w5["query"].lower())
        self.assertIn("single-session", w5["expected"].lower())

    def test_main_writes_manifest_including_w5(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "eval-prompts"
            system_prompt = Path(tmp) / "system-prompt.md"
            system_prompt.write_text("System prompt", encoding="utf-8")

            def fake_run_retrieval(query):
                return {
                    "status": "ok",
                    "prompt_package": f"PROMPT for: {query}",
                    "route": {
                        "workflow": "workflow_5_next_session_plan",
                        "intent": "Next-session plan",
                    },
                    "selected_chunks": [
                        {"chunk_id": "next-session-planning-bounded-next-session-plan-001"}
                    ],
                }

            with patch.object(build_workflow_eval_prompts, "OUT_DIR", out_dir), patch.object(
                build_workflow_eval_prompts, "SYSTEM_PROMPT", system_prompt
            ), patch.object(
                build_workflow_eval_prompts,
                "run_retrieval",
                side_effect=fake_run_retrieval,
            ):
                build_workflow_eval_prompts.main()

            manifest = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))

        eval_ids = {item["id"] for item in manifest}
        self.assertIn("W5-001", eval_ids)
        w5 = next(item for item in manifest if item["id"] == "W5-001")
        self.assertEqual(w5["workflow"], "workflow_5_next_session_plan")
        self.assertIn(
            "next-session-planning-bounded-next-session-plan-001",
            w5["chunks"],
        )


if __name__ == "__main__":
    unittest.main()
