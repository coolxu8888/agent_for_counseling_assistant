import json
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run-retrieval.ps1"


class RunRetrievalTest(unittest.TestCase):
    def run_retrieval(self, query):
        completed = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(SCRIPT),
                "-Query",
                query,
                "-SummaryOnly",
                "-Json",
            ],
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        return json.loads(completed.stdout)

    def test_routes_next_session_plan_query_to_w5(self):
        payload = self.run_retrieval(
            "Create a CBT next-session plan for this de-identified case with risk check points."
        )

        self.assertEqual(payload["status"], "OK")
        self.assertEqual(payload["route"]["workflow"], "workflow_5_next_session_plan")
        chunk_ids = [chunk["chunk_id"] for chunk in payload["selected_chunks"]]
        self.assertIn("next-session-planning-bounded-next-session-plan-001", chunk_ids)

    def test_routes_counseling_roadmap_query_to_w6(self):
        payload = self.run_retrieval(
            "Create an integrative counseling roadmap for this de-identified case with phases, hypotheses to verify, and risk monitoring checkpoints."
        )

        self.assertEqual(payload["status"], "OK")
        self.assertEqual(payload["route"]["workflow"], "workflow_6_counseling_roadmap")
        chunk_ids = [chunk["chunk_id"] for chunk in payload["selected_chunks"]]
        self.assertIn("roadmap-planning-bounded-counseling-roadmap-001", chunk_ids)

    def test_routes_pre_interview_collection_query_to_w1(self):
        payload = self.run_retrieval(
            "Before tomorrow's first interview, create an intake question guide for what information still needs to be collected."
        )

        self.assertEqual(payload["status"], "OK")
        self.assertEqual(payload["route"]["workflow"], "workflow_1_intake_form")

    def test_routes_bps_case_background_query_to_w2(self):
        payload = self.run_retrieval(
            "Organize this de-identified case into a biopsychosocial case background with protective factors and risk follow-up questions."
        )

        self.assertEqual(payload["status"], "OK")
        self.assertEqual(payload["route"]["workflow"], "workflow_2_case_summary")

    def test_routes_mixed_language_bps_background_to_w2_even_when_negating_session_note(self):
        payload = self.run_retrieval(
            "Please organize these mixed-language intake notes into a BPS case background, not a session note. "
            "来访者近两周 sleep worse after family conflict, still attending class, and sometimes says she wants to disappear, "
            "but there is no reported plan. Separate known facts, working hypotheses, information gaps, protective factors, and risk follow-up questions."
        )

        self.assertEqual(payload["status"], "OK")
        self.assertEqual(payload["route"]["workflow"], "workflow_2_case_summary")
        chunk_ids = [chunk["chunk_id"] for chunk in payload["selected_chunks"]]
        self.assertIn("intake-assessment-biopsychosocial-client-assessment-001", chunk_ids)

    def test_routes_session_note_boundary_case_background_to_w2_when_negating_counseling_record(self):
        payload = self.run_retrieval(
            "Please turn today's session note into a BPS case background for supervision, not a counseling record. "
            "Separate known facts, working hypotheses, protective factors, and risk follow-up questions while keeping the material de-identified and bounded."
        )

        self.assertEqual(payload["status"], "OK")
        self.assertEqual(payload["route"]["workflow"], "workflow_2_case_summary")
        chunk_ids = [chunk["chunk_id"] for chunk in payload["selected_chunks"]]
        self.assertIn("intake-assessment-biopsychosocial-client-assessment-001", chunk_ids)

    def test_routes_post_session_note_query_to_w3_even_when_it_mentions_first_interview(self):
        payload = self.run_retrieval(
            "These are my first interview notes from today. Turn them into a counseling record with a risk update and next session focus."
        )

        self.assertEqual(payload["status"], "OK")
        self.assertEqual(payload["route"]["workflow"], "workflow_3_session_note")

    def test_routes_chinese_first_completed_initial_interview_summary_to_summary_intent(self):
        payload = self.run_retrieval(
            "这是一份已经完成的初访记录，不是 session note 或 counseling record。"
            "请按固定初访总结模板整理，分开 known facts、unclear or missing facts、follow-up questions，"
            "并把风险线索单独保留但不要下最终风险等级。"
        )

        self.assertEqual(payload["status"], "OK")
        self.assertEqual(payload["route"]["workflow"], "workflow_1_intake_form")
        self.assertEqual(payload["route"]["intent"], "初始访谈材料总结")
        chunk_ids = [chunk["chunk_id"] for chunk in payload["selected_chunks"]]
        self.assertIn("intake-assessment-biopsychosocial-client-assessment-001", chunk_ids)
        self.assertIn("case-recording-cps-professional-materials-recording-001", chunk_ids)

    def test_routes_chinese_first_summary_request_that_negates_birp_to_w1_summary_intent(self):
        payload = self.run_retrieval(
            "请根据首访原始记录整理固定模板总结，保留风险变化线索，不要写成BIRP或咨询记录。"
        )

        self.assertEqual(payload["status"], "OK")
        self.assertEqual(payload["route"]["workflow"], "workflow_1_intake_form")
        self.assertEqual(payload["route"]["intent"], "初始访谈材料总结")
        chunk_ids = [chunk["chunk_id"] for chunk in payload["selected_chunks"]]
        self.assertIn("intake-assessment-biopsychosocial-client-assessment-001", chunk_ids)
        self.assertIn("case-recording-cps-professional-materials-recording-001", chunk_ids)

    def test_routes_chinese_first_summary_request_that_negates_soap_to_w1_summary_intent(self):
        payload = self.run_retrieval(
            "请根据首访原始记录整理固定模板总结，保留风险变化线索，不要写成SOAP或session note。"
        )

        self.assertEqual(payload["status"], "OK")
        self.assertEqual(payload["route"]["workflow"], "workflow_1_intake_form")
        self.assertEqual(payload["route"]["intent"], "初始访谈材料总结")
        chunk_ids = [chunk["chunk_id"] for chunk in payload["selected_chunks"]]
        self.assertIn("intake-assessment-biopsychosocial-client-assessment-001", chunk_ids)
        self.assertIn("case-recording-cps-professional-materials-recording-001", chunk_ids)

    def test_routes_mixed_next_session_and_roadmap_query_to_w6(self):
        payload = self.run_retrieval(
            "Map the next several sessions into a phased counseling roadmap, including the immediate next session and later phases."
        )

        self.assertEqual(payload["status"], "OK")
        self.assertEqual(payload["route"]["workflow"], "workflow_6_counseling_roadmap")

    def test_humanistic_conceptualization_retrieval_includes_theory_and_boundary_chunks(self):
        payload = self.run_retrieval(
            "Use a humanistic framework to conceptualize this de-identified case, focusing on felt experience and relational conditions rather than planning the next session."
        )

        self.assertEqual(payload["status"], "OK")
        self.assertEqual(payload["route"]["workflow"], "workflow_4_case_conceptualization")
        chunk_ids = [chunk["chunk_id"] for chunk in payload["selected_chunks"]]
        self.assertIn("theory-frameworks-humanistic-case-conceptualization-001", chunk_ids)
        self.assertIn("ethics-risk-cps-professional-boundary-001", chunk_ids)

    def test_session_note_confidentiality_retrieval_includes_documentation_boundary_chunks(self):
        payload = self.run_retrieval(
            "Write a counseling record from today's session notes. The client asked who can read the record, the counselor reviewed confidentiality limits and documentation boundaries, and there was no current suicide plan."
        )

        self.assertEqual(payload["status"], "OK")
        self.assertEqual(payload["route"]["workflow"], "workflow_3_session_note")
        chunk_ids = [chunk["chunk_id"] for chunk in payload["selected_chunks"]]
        self.assertIn("session-notes-bacp-confidentiality-record-keeping-001", chunk_ids)
        self.assertIn("ethics-risk-cps-informed-consent-confidentiality-001", chunk_ids)

    def test_psychodynamic_single_session_plan_routes_to_w5(self):
        payload = self.run_retrieval(
            "Using a psychodynamic lens, create only the plan for the single upcoming counseling session from this de-identified case, including risk monitoring and optional questions."
        )

        self.assertEqual(payload["status"], "OK")
        self.assertEqual(payload["route"]["workflow"], "workflow_5_next_session_plan")
        chunk_ids = [chunk["chunk_id"] for chunk in payload["selected_chunks"]]
        self.assertIn("next-session-planning-bounded-next-session-plan-001", chunk_ids)
        self.assertIn("theory-frameworks-psychodynamic-next-session-planning-001", chunk_ids)

    def test_integrative_single_session_plan_uses_integrative_planning_chunk(self):
        payload = self.run_retrieval(
            "Using an integrative framework, create only the plan for the single upcoming counseling session from this de-identified case, including risk monitoring, collaboration reminders, and optional between-session work."
        )

        self.assertEqual(payload["status"], "OK")
        self.assertEqual(payload["route"]["workflow"], "workflow_5_next_session_plan")
        self.assertEqual(payload["route"]["intent"], "Integrative next-session plan")
        chunk_ids = [chunk["chunk_id"] for chunk in payload["selected_chunks"]]
        self.assertIn("next-session-planning-bounded-next-session-plan-001", chunk_ids)
        self.assertIn("theory-frameworks-integrative-next-session-planning-001", chunk_ids)

    def test_routes_bilingual_next_session_plan_when_record_format_is_negated(self):
        payload = self.run_retrieval(
            "请先不要写成咨询记录或 session note，只做下一次咨询计划。"
            "Use a humanistic lens, keep it to one upcoming counseling session, include risk check points, "
            "and do not expand into a roadmap."
        )

        self.assertEqual(payload["status"], "OK")
        self.assertEqual(payload["route"]["workflow"], "workflow_5_next_session_plan")
        self.assertEqual(payload["route"]["intent"], "Humanistic next-session plan")
        chunk_ids = [chunk["chunk_id"] for chunk in payload["selected_chunks"]]
        self.assertIn("next-session-planning-bounded-next-session-plan-001", chunk_ids)
        self.assertIn("theory-frameworks-humanistic-next-session-planning-001", chunk_ids)

    def test_humanistic_roadmap_uses_framework_specific_roadmap_chunk(self):
        payload = self.run_retrieval(
            "Create a humanistic counseling roadmap for the next several sessions, keeping the immediate next session inside a broader phased roadmap and preserving risk-monitoring checkpoints."
        )

        self.assertEqual(payload["status"], "OK")
        self.assertEqual(payload["route"]["workflow"], "workflow_6_counseling_roadmap")
        chunk_ids = [chunk["chunk_id"] for chunk in payload["selected_chunks"]]
        self.assertIn("roadmap-planning-bounded-counseling-roadmap-001", chunk_ids)
        self.assertIn("theory-frameworks-humanistic-counseling-roadmap-001", chunk_ids)


if __name__ == "__main__":
    unittest.main()
