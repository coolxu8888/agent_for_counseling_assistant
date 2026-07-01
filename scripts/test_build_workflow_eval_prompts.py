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
        self.assertIn("W1-010", ids)
        self.assertIn("W1-011", ids)
        self.assertIn("W1-012", ids)
        self.assertIn("W1-013", ids)
        self.assertIn("W1-014", ids)
        self.assertIn("W2-005", ids)
        self.assertIn("W2-006", ids)
        self.assertIn("W2-007", ids)
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
        self.assertIn("W5-005", ids)
        self.assertIn("W5-006", ids)
        self.assertIn("W6-004", ids)
        self.assertIn("W6-005", ids)

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

    def test_evals_include_chinese_first_w1_summary_boundary_case(self):
        w1_chinese_first = next(
            item for item in build_workflow_eval_prompts.EVALS if item["id"] == "W1-010"
        )

        self.assertIn("初访记录", w1_chinese_first["query"])
        self.assertIn("session note", w1_chinese_first["query"].lower())
        self.assertIn("chinese-first", w1_chinese_first["expected"].lower())
        self.assertIn("fixed initial interview summary structure", w1_chinese_first["expected"].lower())

    def test_evals_include_chinese_first_w1_summary_birp_boundary_case(self):
        w1_birp_boundary = next(
            item for item in build_workflow_eval_prompts.EVALS if item["id"] == "W1-011"
        )

        self.assertIn("首访原始记录", w1_birp_boundary["query"])
        self.assertIn("birp", w1_birp_boundary["query"].lower())
        self.assertIn("chinese-first", w1_birp_boundary["expected"].lower())
        self.assertIn("record-format negation", w1_birp_boundary["expected"].lower())

    def test_evals_include_chinese_first_w1_summary_soap_boundary_case(self):
        w1_soap_boundary = next(
            item for item in build_workflow_eval_prompts.EVALS if item["id"] == "W1-012"
        )

        self.assertIn("首访原始记录", w1_soap_boundary["query"])
        self.assertIn("soap", w1_soap_boundary["query"].lower())
        self.assertIn("chinese-first", w1_soap_boundary["expected"].lower())
        self.assertIn("record-format negation", w1_soap_boundary["expected"].lower())

    def test_evals_include_chinese_first_w1_summary_dap_boundary_case(self):
        w1_dap_boundary = next(
            item for item in build_workflow_eval_prompts.EVALS if item["id"] == "W1-013"
        )

        self.assertIn("首访原始记录", w1_dap_boundary["query"])
        self.assertIn("dap", w1_dap_boundary["query"].lower())
        self.assertIn("chinese-first", w1_dap_boundary["expected"].lower())
        self.assertIn("record-format negation", w1_dap_boundary["expected"].lower())

    def test_evals_include_loose_chinese_first_w1_summary_soap_boundary_case(self):
        w1_loose_soap_boundary = next(
            item for item in build_workflow_eval_prompts.EVALS if item["id"] == "W1-014"
        )

        self.assertIn("首访材料", w1_loose_soap_boundary["query"])
        self.assertIn("soap", w1_loose_soap_boundary["query"].lower())
        self.assertIn("chinese-first", w1_loose_soap_boundary["expected"].lower())
        self.assertIn("fixed initial interview summary structure", w1_loose_soap_boundary["expected"].lower())

    def test_evals_include_loose_fixed_template_w1_summary_record_boundary_case(self):
        w1_loose_record_boundary = next(
            item for item in build_workflow_eval_prompts.EVALS if item["id"] == "W1-015"
        )

        self.assertIn("固定模板", w1_loose_record_boundary["query"])
        self.assertIn("第一次访谈材料", w1_loose_record_boundary["query"])
        self.assertIn("咨询记录", w1_loose_record_boundary["query"])
        self.assertIn("fixed initial interview summary structure", w1_loose_record_boundary["expected"].lower())

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

    def test_evals_include_w2_session_note_boundary_case(self):
        w2 = next(item for item in build_workflow_eval_prompts.EVALS if item["id"] == "W2-007")

        self.assertIn("session note", w2["query"].lower())
        self.assertIn("case background", w2["query"].lower())
        self.assertIn("supervision", w2["query"].lower())
        self.assertIn("session-record cues", w2["expected"].lower())

    def test_evals_include_w2_conceptualization_boundary_case(self):
        w2 = next(item for item in build_workflow_eval_prompts.EVALS if item["id"] == "W2-008")

        self.assertIn("cbt", w2["query"].lower())
        self.assertIn("case background", w2["query"].lower())
        self.assertIn("case conceptualization", w2["query"].lower())
        self.assertIn("conceptualization negation", w2["expected"].lower())

    def test_evals_include_w2_completed_initial_interview_boundary_case(self):
        w2 = next(item for item in build_workflow_eval_prompts.EVALS if item["id"] == "W2-009")

        self.assertIn("completed first interview notes", w2["query"].lower())
        self.assertIn("bps case background", w2["query"].lower())
        self.assertIn("fixed initial interview summary template", w2["query"].lower())
        self.assertIn("initial-interview-summary negation", w2["expected"].lower())

    def test_evals_include_w2_chinese_completed_initial_interview_boundary_case(self):
        w2 = next(item for item in build_workflow_eval_prompts.EVALS if item["id"] == "W2-010")

        self.assertIn("首访材料", w2["query"])
        self.assertIn("个案背景", w2["query"])
        self.assertIn("固定初访总结模板", w2["query"])
        self.assertIn("chinese-heavy", w2["expected"].lower())

    def test_evals_include_w2_loose_initial_interview_summary_negation_boundary_case(self):
        w2 = next(item for item in build_workflow_eval_prompts.EVALS if item["id"] == "W2-011")

        self.assertIn("completed intake notes", w2["query"].lower())
        self.assertIn("usual initial interview summary", w2["query"].lower())
        self.assertIn("supervision case background", w2["query"].lower())
        self.assertIn("loose initial-interview-summary negation", w2["expected"].lower())

    def test_evals_include_w2_chinese_loose_initial_interview_summary_negation_boundary_case(self):
        w2 = next(item for item in build_workflow_eval_prompts.EVALS if item["id"] == "W2-012")

        self.assertIn("已完成的首访材料", w2["query"])
        self.assertIn("督导讨论用的个案背景", w2["query"])
        self.assertIn("常规初访总结", w2["query"])
        self.assertIn("chinese-heavy loose", w2["expected"].lower())

    def test_evals_include_w5_bilingual_record_negation_case(self):
        w5 = next(item for item in build_workflow_eval_prompts.EVALS if item["id"] == "W5-005")

        self.assertIn("session note", w5["query"].lower())
        self.assertIn("humanistic", w5["query"].lower())
        self.assertIn("bilingual", w5["expected"].lower())
        self.assertIn("one-session planning route", w5["expected"].lower())

    def test_evals_include_w5_negated_roadmap_scope_case(self):
        w5 = next(item for item in build_workflow_eval_prompts.EVALS if item["id"] == "W5-006")

        self.assertIn("humanistic", w5["query"].lower())
        self.assertIn("next counseling session", w5["query"].lower())
        self.assertIn("multi-session roadmap", w5["query"].lower())
        self.assertIn("negated roadmap scope", w5["expected"].lower())

    def test_evals_include_w5_session_note_source_material_boundary_case(self):
        w5 = next(item for item in build_workflow_eval_prompts.EVALS if item["id"] == "W5-007")

        self.assertIn("session notes", w5["query"].lower())
        self.assertIn("next session agenda", w5["query"].lower())
        self.assertIn("rather than a counseling record", w5["query"].lower())
        self.assertIn("source-material record negation", w5["expected"].lower())

    def test_evals_include_w5_chinese_session_note_source_material_boundary_case(self):
        w5 = next(item for item in build_workflow_eval_prompts.EVALS if item["id"] == "W5-008")

        self.assertIn("会谈记录", w5["query"])
        self.assertIn("下一次咨询计划", w5["query"])
        self.assertIn("不要写成咨询记录", w5["query"])
        self.assertIn("chinese-heavy", w5["expected"].lower())

    def test_evals_expand_retrieval_boundary_matrix(self):
        w1 = next(item for item in build_workflow_eval_prompts.EVALS if item["id"] == "W1-006")
        w1_prefill = next(item for item in build_workflow_eval_prompts.EVALS if item["id"] == "W1-007")
        w3 = next(item for item in build_workflow_eval_prompts.EVALS if item["id"] == "W3-006")
        w4 = next(item for item in build_workflow_eval_prompts.EVALS if item["id"] == "W4-003")
        w5 = next(item for item in build_workflow_eval_prompts.EVALS if item["id"] == "W5-003")
        w6 = next(item for item in build_workflow_eval_prompts.EVALS if item["id"] == "W6-003")
        w5_integrative = next(item for item in build_workflow_eval_prompts.EVALS if item["id"] == "W5-004")
        w5_bilingual = next(item for item in build_workflow_eval_prompts.EVALS if item["id"] == "W5-005")
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
        self.assertIn("humanistic", w5_bilingual["query"].lower())
        self.assertIn("record-format negation", w5_bilingual["expected"].lower())
        self.assertIn("humanistic", next(item for item in build_workflow_eval_prompts.EVALS if item["id"] == "W5-006")["query"].lower())
        self.assertIn("session notes", next(item for item in build_workflow_eval_prompts.EVALS if item["id"] == "W5-007")["query"].lower())
        self.assertIn("会谈记录", next(item for item in build_workflow_eval_prompts.EVALS if item["id"] == "W5-008")["query"])
        self.assertIn("psychodynamic", w6_psychodynamic["query"].lower())
        self.assertIn("multi-session roadmap", w6_psychodynamic["expected"].lower())

    def test_evals_include_w3_birp_risk_change_case(self):
        w3 = next(item for item in build_workflow_eval_prompts.EVALS if item["id"] == "W3-007")

        self.assertIn("birp", w3["query"].lower())
        self.assertIn("mixed-language", w3["expected"].lower())
        self.assertIn("risk-change", w3["expected"].lower())

    def test_evals_include_w4_session_note_boundary_case(self):
        w4 = next(item for item in build_workflow_eval_prompts.EVALS if item["id"] == "W4-004")

        self.assertIn("session notes", w4["query"].lower())
        self.assertIn("not a counseling record", w4["query"].lower())
        self.assertIn("conceptualization", w4["expected"].lower())
        self.assertIn("record-format negation", w4["expected"].lower())

    def test_evals_include_bilingual_w4_session_note_boundary_case(self):
        w4 = next(item for item in build_workflow_eval_prompts.EVALS if item["id"] == "W4-005")

        self.assertIn("session note", w4["query"].lower())
        self.assertIn("概念化", w4["query"])
        self.assertIn("咨询记录", w4["query"])
        self.assertIn("bilingual", w4["expected"].lower())
        self.assertIn("record-format negation", w4["expected"].lower())

    def test_evals_include_w6_bilingual_session_note_source_material_boundary_case(self):
        w6 = next(item for item in build_workflow_eval_prompts.EVALS if item["id"] == "W6-005")

        self.assertIn("session note", w6["query"].lower())
        self.assertIn("later phases", w6["query"].lower())
        self.assertIn("咨询记录", w6["query"])
        self.assertIn("source material", w6["expected"].lower())
        self.assertIn("single-session plan", w6["expected"].lower())

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
