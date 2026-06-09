import unittest

from fill_docx_template import build_source_map, find_source_match, normalize_label


class FillDocxTemplateTest(unittest.TestCase):
    def sample_w3(self):
        return {
            "workflow": "W3",
            "document_type": "session_note",
            "title": "本次咨询记录",
            "sections": [
                {"heading": "本次主题", "content": "讨论分手后的低落情绪。"},
                {"heading": "咨询师干预", "content": "支持性回应并讨论社会支持。"},
            ],
            "risk_change": {"content": "出现被动自杀意念，无具体计划。"},
            "next_session_focus": ["继续评估安全情况", "回顾联系朋友的结果"],
            "missing_information": ["风险意念频率与强度"],
            "boundary_notes": ["本记录不替代正式风险评估。"],
        }

    def test_normalize_label_removes_punctuation_and_placeholders(self):
        self.assertEqual(normalize_label(" 风险变化：____ "), "风险变化")

    def test_build_source_map_exposes_w3_core_fields(self):
        source_map = build_source_map(self.sample_w3())

        match = find_source_match("风险变化", source_map)

        self.assertIsNotNone(match)
        self.assertEqual(match["source_path"], "risk_change.content")
        self.assertEqual(match["value"], "出现被动自杀意念，无具体计划。")

    def test_find_source_match_supports_medium_contains_match(self):
        source_map = build_source_map(self.sample_w3())

        match = find_source_match("下次咨询重点安排", source_map)

        self.assertIsNotNone(match)
        self.assertEqual(match["confidence"], "medium")
        self.assertIn("继续评估安全情况", match["value"])


if __name__ == "__main__":
    unittest.main()
