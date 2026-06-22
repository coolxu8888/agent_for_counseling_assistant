import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from render_docx import main, parse_args, render_docx


class RenderDocxTest(unittest.TestCase):
    def minimal_w1(self):
        return {
            "workflow": "W1",
            "document_type": "intake_form",
            "title": "初访信息收集表",
            "sections": [
                {
                    "heading": "风险评估",
                    "fields": [
                        {
                            "label": "自杀意念",
                            "value": "",
                            "required": False,
                            "sensitive": True,
                            "risk_signal": True,
                            "notes": "待补充",
                        }
                    ],
                }
            ],
            "boundary_notes": ["本表不构成诊断。"],
        }

    def minimal_w2(self):
        return {
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
            "suggested_questions": ["睡眠问题持续多久？"],
            "boundary_notes": ["不构成诊断。"],
        }

    def minimal_w1_summary(self):
        return {
            "workflow": "W1",
            "document_type": "initial_session_summary",
            "title": "Initial interview summary",
            "sections": [
                {
                    "id": "main_distress",
                    "heading": "Main distress",
                    "known_facts": ["Recent low mood after a breakup."],
                    "unclear_or_missing": ["Duration still needs verification."],
                    "follow_up_questions": ["How long has the low mood been present?"],
                },
                {
                    "id": "risk_crisis",
                    "heading": "Risk and crisis information",
                    "known_facts": ["Passive disappearance language was documented."],
                    "unclear_or_missing": ["No information about access to means."],
                    "follow_up_questions": ["Ask about intent, plan, means, and protective factors."],
                },
            ],
            "summary_guidance": ["Separate known facts, unclear facts, and follow-up questions."],
            "boundary_notes": ["Organize only the provided material and do not output a final diagnosis or risk rating."],
        }

    def minimal_w2_bps(self):
        return {
            "workflow": "W2",
            "document_type": "case_summary",
            "title": "Case background organization",
            "presenting_concerns": ["Sleep disruption and conflict distress."],
            "case_overview": {
                "known_facts": ["Adult client, married, one child."],
                "working_hypotheses": ["Role strain may be contributing to distress."],
                "information_gaps": ["Prior coping history is incomplete."],
            },
            "bio_psycho_social": {
                "biological": {
                    "known_facts": ["Insomnia and fatigue."],
                    "working_hypotheses": ["Sleep disruption may worsen emotional reactivity."],
                    "information_gaps": ["Appetite changes are not documented."],
                    "follow_up_questions": ["How many hours is the client sleeping?"],
                },
                "psychological": {
                    "known_facts": ["Feels wronged and suppresses distress before outbursts."],
                    "working_hypotheses": ["Emotion suppression may be part of the pattern."],
                    "information_gaps": ["Core beliefs are not yet clear."],
                    "follow_up_questions": ["What thoughts appear before withdrawal?"],
                },
                "social": {
                    "known_facts": ["Work stress and partner conflict are active."],
                    "working_hypotheses": ["Limited support may intensify stress."],
                    "information_gaps": ["Support outside the family is unclear."],
                    "follow_up_questions": ["Who can offer support outside the home?"],
                },
            },
            "protective_factors": ["Help-seeking and parenting responsibilities."],
            "risk_formulation": {
                "observed_clues": ["No self-harm or suicide content was reported."],
                "missing_or_unclear": ["Direct risk inquiry results are not documented."],
                "follow_up_questions": ["Ask directly about self-harm, suicide, violence, and alcohol use."],
            },
            "recommended_focus": ["Clarify the conflict timeline and existing supports."],
            "boundary_notes": ["This is a counselor-facing organizer, not a diagnosis or final risk judgment."],
        }

    def minimal_w3(self):
        return {
            "workflow": "W3",
            "document_type": "session_note",
            "title": "本次咨询记录",
            "sections": [
                {"heading": "本次主题", "content": "主题"},
                {"heading": "风险变化", "content": "材料中未提供风险相关信息"},
            ],
            "risk_change": {"content": "材料中未提供风险相关信息"},
            "next_session_focus": ["继续讨论表达方式"],
            "missing_information": ["来访者状态未提供"],
            "boundary_notes": ["本记录不替代咨询师专业判断。"],
        }

    def minimal_w5(self):
        return {
            "workflow": "W5",
            "document_type": "next_session_plan",
            "title": "Next session plan",
            "selected_framework": "cbt",
            "session_goal": "Explore the criticism-anxiety cycle in one upcoming session.",
            "focus_areas": ["Map triggers, automatic thoughts, and avoidance after criticism."],
            "planned_interventions": ["Use a brief in-session thought record and collaborative review."],
            "suggested_questions": ["What does the client predict will happen after one mistake?"],
            "risk_monitoring": ["Re-check suicide ideation, self-harm, sleep disruption, and escalation in avoidance."],
            "between_session_tasks": ["Invite the client to record one criticism episode if clinically appropriate."],
            "do_not_do": ["Do not turn this into a multi-session roadmap or assign unsupported exposure tasks."],
            "boundary_notes": ["This is a bounded next-session plan, not a diagnosis or full treatment plan."],
        }

    def minimal_w6(self):
        return {
            "workflow": "W6",
            "document_type": "counseling_roadmap",
            "title": "Counseling roadmap",
            "selected_framework": "integrative",
            "overview": "A phased roadmap for counselor planning that should evolve with ongoing assessment.",
            "phases": [
                {
                    "phase_name": "Engagement and assessment",
                    "goals": ["Clarify goals and map the current anxiety-avoidance cycle."],
                    "markers_to_monitor": ["Sleep disruption", "withdrawal after conflict"],
                }
            ],
            "hypotheses_to_verify": ["Interpersonal criticism may trigger shame and withdrawal."],
            "session_focus_options": ["Review one recent conflict and identify what the client predicted would happen."],
            "risk_monitoring_checkpoints": ["Re-check suicide ideation, self-harm, and deterioration in functioning at each phase."],
            "collaboration_referral_reminders": ["Coordinate referral discussion only if new needs emerge and according to counselor judgment."],
            "missing_information": ["History of prior counseling response is not yet documented."],
            "do_not_do": ["Do not present this as a diagnosis, fixed duration, or guaranteed treatment course."],
            "boundary_notes": ["This roadmap is a working aid, not a rigid treatment prescription."],
        }

    def read_document_xml(self, docx_path):
        with zipfile.ZipFile(docx_path) as package:
            return package.read("word/document.xml").decode("utf-8")

    def test_render_docx_creates_minimal_ooxml_package(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_path = Path(tmp) / "output.docx"

            check = render_docx(self.minimal_w3(), output_path)

            with zipfile.ZipFile(output_path) as package:
                names = set(package.namelist())

        self.assertEqual(check["status"], "PASS")
        self.assertIn("[Content_Types].xml", names)
        self.assertIn("_rels/.rels", names)
        self.assertIn("word/document.xml", names)
        self.assertIn("word/styles.xml", names)

    def test_render_w1_contains_title_risk_section_and_table(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_path = Path(tmp) / "w1.docx"

            render_docx(self.minimal_w1(), output_path)
            document_xml = self.read_document_xml(output_path)

        self.assertIn("初访信息收集表", document_xml)
        self.assertIn("风险评估", document_xml)
        self.assertIn("自杀意念", document_xml)
        self.assertIn("<w:tbl>", document_xml)

    def test_render_w2_contains_bps_and_questions(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_path = Path(tmp) / "w2.docx"

            render_docx(self.minimal_w2(), output_path)
            document_xml = self.read_document_xml(output_path)

        self.assertIn("个案信息整理", document_xml)
        self.assertIn("Biological dimension", document_xml)
        self.assertIn("Psychological dimension", document_xml)
        self.assertIn("Social dimension", document_xml)
        self.assertIn("Follow-up questions", document_xml)

    def test_render_w1_initial_summary_contains_known_unclear_and_follow_up_lists(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_path = Path(tmp) / "w1-summary.docx"

            render_docx(self.minimal_w1_summary(), output_path)
            document_xml = self.read_document_xml(output_path)

        self.assertIn("Initial interview summary", document_xml)
        self.assertIn("Main distress", document_xml)
        self.assertIn("Known facts", document_xml)
        self.assertIn("Unclear or missing", document_xml)
        self.assertIn("Follow-up questions", document_xml)

    def test_render_w2_bps_contains_dimension_splits_and_risk_follow_up(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_path = Path(tmp) / "w2-bps.docx"

            render_docx(self.minimal_w2_bps(), output_path)
            document_xml = self.read_document_xml(output_path)

        self.assertIn("Case background organization", document_xml)
        self.assertIn("Presenting concerns", document_xml)
        self.assertIn("Case overview", document_xml)
        self.assertIn("Biological dimension", document_xml)
        self.assertIn("Psychological dimension", document_xml)
        self.assertIn("Social dimension", document_xml)
        self.assertIn("Working hypotheses", document_xml)
        self.assertIn("Follow-up questions", document_xml)
        self.assertIn("Risk formulation", document_xml)
        self.assertIn("Recommended focus", document_xml)

    def test_render_w6_contains_phases_and_referral_reminders(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_path = Path(tmp) / "w6.docx"

            render_docx(self.minimal_w6(), output_path)
            document_xml = self.read_document_xml(output_path)

        self.assertIn("Counseling roadmap", document_xml)
        self.assertIn("Engagement and assessment", document_xml)
        self.assertIn("collaboration_referral_reminders", document_xml.lower())
        self.assertIn("diagnosis, fixed duration, or guaranteed treatment course", document_xml)

    def test_render_w3_contains_session_sections(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_path = Path(tmp) / "w3.docx"

            render_docx(self.minimal_w3(), output_path)
            document_xml = self.read_document_xml(output_path)

        self.assertIn("本次咨询记录", document_xml)
        self.assertIn("本次主题", document_xml)
        self.assertIn("风险变化", document_xml)
        self.assertIn("下次咨询重点", document_xml)

    def test_render_w5_contains_bounded_plan_sections(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_path = Path(tmp) / "w5.docx"

            render_docx(self.minimal_w5(), output_path)
            document_xml = self.read_document_xml(output_path)

        self.assertIn("Next session plan", document_xml)
        self.assertIn("Session goal", document_xml)
        self.assertIn("Planned interventions", document_xml)
        self.assertIn("Between-session tasks", document_xml)
        self.assertIn("Do not do", document_xml)

    def test_parse_args_accepts_input_output_and_check_path(self):
        args = parse_args(["--input", "in.json", "--output", "out.docx", "--check-output", "check.json"])

        self.assertEqual(args.input, "in.json")
        self.assertEqual(args.output, "out.docx")
        self.assertEqual(args.check_output, "check.json")

    def test_main_writes_docx_and_check_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            input_path = tmp_path / "structured_output.json"
            output_path = tmp_path / "output.docx"
            check_path = tmp_path / "docx_check.json"
            input_path.write_text(json.dumps(self.minimal_w3(), ensure_ascii=False), encoding="utf-8")

            code = main(["--input", str(input_path), "--output", str(output_path), "--check-output", str(check_path)])

            check = json.loads(check_path.read_text(encoding="utf-8"))
            output_exists = output_path.exists()

        self.assertEqual(code, 0)
        self.assertTrue(output_exists)
        self.assertEqual(check["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
