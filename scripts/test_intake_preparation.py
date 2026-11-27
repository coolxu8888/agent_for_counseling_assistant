"""Synthetic regressions for W1 preparation requests; no case data or API calls."""

import unittest

from run_agent import build_prompt_package, detect_w1_mode, normalize_workflow


class IntakePreparationTest(unittest.TestCase):
    def test_explicit_pre_interview_request_is_not_a_completed_summary(self):
        for text in (
            "请为明天的首访前准备信息收集表。还没有见到来访者。",
            "首次访谈前，请基于预约资料准备提问提纲。",
            "第一次访谈尚未进行，请准备初访信息收集表。",
            "明天首次访谈，请基于预约资料准备信息收集表和中英提问。",
            "第一次访谈还没开始，请准备提纲。",
            "请帮我准备首访提问提纲。",
        ):
            with self.subTest(text=text):
                self.assertEqual(detect_w1_mode(text), "intake_prep")

    def test_completed_interview_summary_still_uses_summary_mode(self):
        for text in (
            "首访已经完成，请根据原始记录整理固定模板总结。",
            "首访已经完成，请结合首访前准备的资料和访谈记录整理总结。",
            "请整理首次访谈笔记，保留仍需核实的问题。",
            "以下是首次访谈的原始记录，请整理为结构化摘要。",
            "以下是第一次访谈的笔记，请梳理已知事实和信息缺口。",
            "首访刚结束，请根据下面的会谈内容整理总结。",
        ):
            with self.subTest(text=text):
                self.assertEqual(detect_w1_mode(text), "initial_interview_summary")

    def test_intake_prompt_has_one_applicable_document_schema(self):
        prompt = build_prompt_package(
            normalize_workflow("W1"),
            "请生成初访前信息收集表。尚未与来访者会谈。",
            [],
            structured=True,
        )
        self.assertIn('"document_type": "intake_form"', prompt)
        self.assertNotIn('"document_type": "initial_session_summary"', prompt)
        self.assertNotIn("每个 section 都必须拆成 known_facts", prompt)


if __name__ == "__main__":
    unittest.main()
