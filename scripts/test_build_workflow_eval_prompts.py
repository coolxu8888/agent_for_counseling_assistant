import json
import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

MODULE_PATH = Path(__file__).resolve().parent / "build_workflow_eval_prompts.py"
SPEC = importlib.util.spec_from_file_location("build_workflow_eval_prompts", MODULE_PATH)
build_workflow_eval_prompts = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(build_workflow_eval_prompts)


class BuildWorkflowEvalPromptsTest(unittest.TestCase):
    def test_evals_include_w5_next_session_plan(self):
        w5 = next(
            item for item in build_workflow_eval_prompts.EVALS if item["id"] == "W5-001"
        )

        self.assertIn("next-session plan", w5["query"].lower())
        self.assertIn("single-session", w5["expected"].lower())

    def test_evals_include_w6_counseling_roadmap(self):
        w6 = next(
            item for item in build_workflow_eval_prompts.EVALS if item["id"] == "W6-001"
        )

        self.assertIn("counseling roadmap", w6["query"].lower())
        self.assertIn("multi-session", w6["expected"].lower())

    def test_evals_include_ambiguity_and_mixed_intent_cases(self):
        ids = {item["id"] for item in build_workflow_eval_prompts.EVALS}

        self.assertIn("W1-004", ids)
        self.assertIn("W1-005", ids)
        self.assertIn("W1-007", ids)
        self.assertIn("W1-008", ids)
        self.assertIn("W1-009", ids)
        self.assertIn("W2-005", ids)
        self.assertIn("W2-006", ids)
        self.assertIn("W3-004", ids)
        self.assertIn("W3-007", ids)
        self.assertIn("W5-002", ids)
        self.assertIn("W6-002", ids)
        self.assertIn("W1-006", ids)
        self.assertIn("W3-006", ids)
        self.assertIn("W4-003", ids)
        self.assertIn("W5-003", ids)
        self.assertIn("W6-003", ids)
        self.assertIn("W5-004", ids)
        self.assertIn("W6-004", ids)

    def test_evals_include_bilingual_intent_routing_case(self):
        w1_bilingual = next(
            item for item in build_workflow_eval_prompts.EVALS if item["id"] == "W1-008"
        )

        self.assertIn("first interview notes", w1_bilingual["query"].lower())
        self.assertIn("session note", w1_bilingual["query"].lower())
        self.assertIn("bilingual", w1_bilingual["expected"].lower())
        self.assertIn("fixed initial interview summary structure", w1_bilingual["expected"].lower())

    def test_evals_include_mixed_language_w1_summary_case(self):
        w1_mixed = next(
            item for item in build_workflow_eval_prompts.EVALS if item["id"] == "W1-009"
        )

        self.assertIn("completed first interview notes", w1_mixed["query"].lower())
        self.assertIn("sleep has been worse", w1_mixed["query"].lower())
        self.assertIn("mixed-language", w1_mixed["expected"].lower())
        self.assertIn("risk clues", w1_mixed["expected"].lower())

    def test_evals_include_w2_bps_background_organizer(self):
        w2 = next(item for item in build_workflow_eval_prompts.EVALS if item["id"] == "W2-005")

        self.assertIn("biopsychosocial", w2["query"].lower())
        self.assertIn("protective factors", w2["expected"].lower())
        self.assertIn("risk follow-up", w2["expected"].lower())

    def test_evals_include_bilingual_w2_background_case(self):
        w2 = next(item for item in build_workflow_eval_prompts.EVALS if item["id"] == "W2-006")

        self.assertIn("bps", w2["query"].lower())
        self.assertIn("known facts", w2["expected"].lower())
        self.assertIn("mixed-language", w2["expected"].lower())
        self.assertIn("risk follow-up", w2["expected"].lower())

    def test_evals_expand_retrieval_boundary_matrix(self):
        w1 = next(item for item in build_workflow_eval_prompts.EVALS if item["id"] == "W1-006")
        w1_prefill = next(item for item in build_workflow_eval_prompts.EVALS if item["id"] == "W1-007")
        w3 = next(item for item in build_workflow_eval_prompts.EVALS if item["id"] == "W3-006")
        w4 = next(item for item in build_workflow_eval_prompts.EVALS if item["id"] == "W4-003")
        w5 = next(item for item in build_workflow_eval_prompts.EVALS if item["id"] == "W5-003")
        w6 = next(item for item in build_workflow_eval_prompts.EVALS if item["id"] == "W6-003")
        w5_integrative = next(item for item in build_workflow_eval_prompts.EVALS if item["id"] == "W5-004")
        w6_psychodynamic = next(item for item in build_workflow_eval_prompts.EVALS if item["id"] == "W6-004")

        self.assertIn("confidentiality", w1["query"].lower())
        self.assertIn("risk", w1["expected"].lower())
        self.assertIn("prefill", w1_prefill["query"].lower())
        self.assertIn("roommate-conflict", w1_prefill["expected"].lower())
        self.assertIn("confidentiality", w3["expected"].lower())
        self.assertIn("humanistic", w4["query"].lower())
        self.assertIn("avoid drifting into a next-session plan", w4["expected"].lower())
        self.assertIn("psychodynamic", w5["query"].lower())
        self.assertIn("single upcoming session", w5["expected"].lower())
        self.assertIn("humanistic", w6["query"].lower())
        self.assertIn("phased roadmap", w6["expected"].lower())
        self.assertIn("integrative", w5_integrative["query"].lower())
        self.assertIn("counselor judgment", w5_integrative["expected"].lower())
        self.assertIn("psychodynamic", w6_psychodynamic["query"].lower())
        self.assertIn("multi-session roadmap", w6_psychodynamic["expected"].lower())

    def test_evals_include_w3_birp_risk_change_case(self):
        w3 = next(item for item in build_workflow_eval_prompts.EVALS if item["id"] == "W3-007")

        self.assertIn("birp", w3["query"].lower())
        self.assertIn("mixed-language", w3["expected"].lower())
        self.assertIn("risk-change", w3["expected"].lower())

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
        self.assertIn("W6-001", eval_ids)


if __name__ == "__main__":
    unittest.main()
