import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from render_docx import WORD_NS, main, parse_args, render_docx


NS = {"w": WORD_NS}
W = f"{{{WORD_NS}}}"


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

    def bilingual_w1(self):
        return {
            "workflow": "W1",
            "document_type": "intake_form",
            "title": "初访准备 & Intake <guide>",
            "known_clues": ["顶层线索 A & B <初次访谈>", "Top-level source: uses \"weekly\" check-ins."],
            "sections": [
                {
                    "heading": "日常安排 & Routine",
                    "content": "栏目说明：保留 <原文> & context。",
                    "fields": [
                        {
                            "label": "活动偏好 <A>",
                            "value": "喜欢阅读 & walking。",
                            "required": True,
                            "sensitive": False,
                            "risk_signal": False,
                            "notes": "记录原话：\"A < B\"。",
                            "suggested_questions": [
                                "你偏好阅读还是散步？ English: Do you prefer reading & walking?",
                                "每次活动时长是否 < 30 分钟？ English: Is each activity < 30 minutes?",
                            ],
                            "known_clues_used": ["字段一来源：偏好 A & B。", "Field-one source: said \"reading\"."],
                        },
                        {
                            "label": "每周安排",
                            "value": "",
                            "required": False,
                            "sensitive": True,
                            "risk_signal": True,
                            "notes": "按每周频次记录。",
                            "suggested_questions": [
                                "一周安排几次？ English: How many times per week?",
                                "哪些安排最方便？ English: Which times work best?",
                            ],
                            "known_clues_used": ["字段二来源：每周安排尚未确认。"],
                        },
                    ],
                },
                {
                    "heading": "支持与资源",
                    "fields": [
                        {
                            "label": "现有资源",
                            "value": "图书馆",
                            "required": False,
                            "sensitive": False,
                            "risk_signal": False,
                            "notes": "核对开放时间。",
                            "suggested_questions": [
                                "你会使用哪些资源？ English: Which resources do you use?",
                                "还想了解什么？ English: What else would you like to know?",
                            ],
                            "known_clues_used": ["字段三来源：提及图书馆。"],
                        }
                    ],
                },
            ],
            "boundary_notes": ["边界说明：仅用于访谈准备 & review。"],
        }

    def test_render_w1_keeps_every_bilingual_question_verbatim_and_in_field_order(self):
        data = self.bilingual_w1()
        with tempfile.TemporaryDirectory() as tmp:
            output_path = Path(tmp) / "w1-bilingual.docx"
            render_docx(data, output_path)
            document = ET.fromstring(self.read_document_xml(output_path))
        paragraphs = ["".join(p.itertext()) for p in document.findall(".//w:body/w:p", NS)]
        question_paragraphs = [text for text in paragraphs if "English:" in text]
        expected_questions = [
            "你偏好阅读还是散步？ English: Do you prefer reading & walking?",
            "每次活动时长是否 < 30 分钟？ English: Is each activity < 30 minutes?",
            "一周安排几次？ English: How many times per week?",
            "哪些安排最方便？ English: Which times work best?",
            "你会使用哪些资源？ English: Which resources do you use?",
            "还想了解什么？ English: What else would you like to know?",
        ]
        self.assertEqual(len(question_paragraphs), 6)
        for question, paragraph_text in zip(expected_questions, question_paragraphs):
            self.assertIn(question, paragraph_text)
        all_text = "\n".join(paragraphs)
        self.assertIn("初访准备 & Intake <guide>", all_text)
        self.assertLess(all_text.index("活动偏好 <A>"), all_text.index(expected_questions[0]))
        self.assertLess(all_text.index(expected_questions[1]), all_text.index("每周安排"))
        self.assertLess(all_text.index("现有资源"), all_text.index(expected_questions[4]))
        self.assertIsNone(document.find(".//w:tbl", NS))

    def test_render_w1_formats_object_clues_with_readable_labels_and_keeps_extra_keys(self):
        data = self.minimal_w1()
        data["known_clues"] = [
            {
                "id": "K1",
                "content": "偏好阅读 & walking <周末>。",
                "source": "咨询师提供的 \"原话\"。",
                "source_type": "counselor_input",
                "status": "reported",
                "extra_context": "补充内容 <A & B>。",
            },
            "字符串线索仍按原文保留。",
        ]
        risk = data["sections"][0]
        risk["content"] = "风险信息仍待核实。"
        risk["fields"][0]["notes"] = "保留原话与信息来源。"
        risk["fields"][0]["known_clues_used"] = ["K1"]
        with tempfile.TemporaryDirectory() as tmp:
            output_path = Path(tmp) / "w1-object-clues.docx"
            render_docx(data, output_path)
            document = ET.fromstring(self.read_document_xml(output_path))
        text = "\n".join("".join(p.itertext()) for p in document.findall(".//w:body/w:p", NS))
        for expected in [
            "K1：偏好阅读 & walking <周末>。",
            '来源：咨询师提供的 "原话"。',
            "来源类型：counselor_input",
            "extra_context：补充内容 <A & B>。",
            "字符串线索仍按原文保留。",
            "风险信息仍待核实。",
            "自杀意念",
            "保留原话与信息来源。",
            "本表不构成诊断。",
        ]:
            self.assertIn(expected, text)
        self.assertNotIn("source_type:", text)
        self.assertNotIn("content:", text)
        self.assertNotIn("内容：偏好阅读", text)
        for marker in ("status", "reported", "状态", "必填", "敏感", "风险信号"):
            self.assertNotIn(marker, text)
        self.assertIn("使用的已知线索：K1", text)
        self.assertLess(text.index("风险评估"), text.index("已提供线索"))
        self.assertLess(text.index("边界说明"), text.index("已提供线索"))
        clue_paragraph = next(
            "".join(p.itertext()) for p in document.findall(".//w:body/w:p", NS)
            if "偏好阅读 & walking <周末>。" in "".join(p.itertext())
        )
        self.assertTrue(clue_paragraph.startswith("K1："))

    def test_w1_package_has_linked_readable_styles_and_flowing_body(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_path = Path(tmp) / "w1-styles.docx"
            render_docx(self.bilingual_w1(), output_path)
            with zipfile.ZipFile(output_path) as package:
                document = ET.fromstring(package.read("word/document.xml"))
                styles = ET.fromstring(package.read("word/styles.xml"))
                relationships = ET.fromstring(package.read("word/_rels/document.xml.rels"))
        self.assertTrue(any(
            relation.get("Type", "").endswith("/styles") and relation.get("Target") == "styles.xml"
            for relation in relationships
        ))
        defaults = styles.find("w:docDefaults/w:rPrDefault/w:rPr", NS)
        self.assertIsNotNone(defaults)
        self.assertEqual(defaults.find("w:color", NS).get(W + "val"), "000000")
        self.assertEqual(defaults.find("w:sz", NS).get(W + "val"), "22")
        for style_id in ["Title", "Heading1", "Heading2"]:
            style = styles.find(f'w:style[@w:styleId="{style_id}"]', NS)
            self.assertIsNotNone(style)
            self.assertIsNotNone(style.find("w:pPr/w:keepNext", NS))
        self.assertIsNone(styles.find("w:docDefaults/w:pPrDefault/w:pPr/w:keepNext", NS))
        self.assertIsNone(styles.find("w:docDefaults/w:pPrDefault/w:pPr/w:keepLines", NS))
        styles_used = [p.get(W + "val") for p in document.findall(".//w:pStyle", NS)]
        self.assertIn("Title", styles_used)
        self.assertIn("Heading1", styles_used)
        self.assertIn("Heading2", styles_used)
        self.assertIsNone(document.find(".//w:keepLines", NS))
        margins = document.find(".//w:sectPr/w:pgMar", NS)
        for side in ["top", "right", "bottom", "left"]:
            self.assertEqual(margins.get(W + side), "1440")

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

    def test_render_w3_dap_contains_record_format_and_risk_follow_up(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_path = Path(tmp) / "w3-dap.docx"
            data = {
                "workflow": "W3",
                "document_type": "session_note",
                "title": "DAP counseling record",
                "record_format": "DAP",
                "sections": [
                    {"heading": "Data", "content": "Client reported lower anxiety but ongoing presentation worry."},
                    {"heading": "Assessment", "content": "Performance-threat thinking may still be active."},
                    {"heading": "Plan", "content": "Review coping rehearsal and presentation follow-through next time."},
                    {"heading": "Risk change", "content": "No new self-harm or suicide escalation was documented."},
                ],
                "risk_change": {
                    "content": "No new self-harm or suicide escalation was documented.",
                    "change_documentation": ["The note does not describe a new escalation in self-harm, suicide, violence, or substance risk."],
                    "follow_up_actions": ["Re-check ideation, access to means, and environmental safety if concern rises."],
                },
                "next_session_focus": ["Review the presentation outcome and coping follow-through."],
                "missing_information": ["No direct counselor observation was documented in the source note."],
                "boundary_notes": ["This is a counselor-facing record, not a diagnosis or final risk judgment."],
            }

            render_docx(data, output_path)
            document_xml = self.read_document_xml(output_path)

        self.assertIn("Record format", document_xml)
        self.assertIn("DAP", document_xml)
        self.assertIn("Risk follow-up actions", document_xml)

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
