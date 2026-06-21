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
                            "notes": "待填写",
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
        self.assertIn("生物维度", document_xml)
        self.assertIn("心理维度", document_xml)
        self.assertIn("社会维度", document_xml)
        self.assertIn("建议进一步询问", document_xml)

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
