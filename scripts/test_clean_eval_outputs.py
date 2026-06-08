import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from clean_eval_outputs import (
    clean_all,
    clean_ui_text,
    display_path,
    extract_final_answer,
    run_dimension_rubric,
    run_rule_checks,
)


class CleanEvalOutputsTest(unittest.TestCase):
    def test_extracts_answer_after_reasoning_and_before_marker(self):
        raw = """
系统提示词
USER_INPUT:
给我一个初访信息收集表。

At the very end, output exactly one separate line: EVAL_DONE_W1_001
\ufffc
已思考（用时 3 秒）
\ufffc
我们需要生成初访信息收集表，不能诊断。
\ufffc
初访信息收集表（咨询师访谈版）
一、基本信息
六、风险评估
EVAL_DONE_W1_001
本回答由 AI 生成，内容仅供参考，请仔细甄别。
"""
        answer = extract_final_answer(raw, "W1-001")
        self.assertIn("初访信息收集表", answer)
        self.assertIn("风险评估", answer)
        self.assertNotIn("系统提示词", answer)
        self.assertNotIn("已思考", answer)
        self.assertNotIn("我们需要生成", answer)
        self.assertNotIn("EVAL_DONE", answer)

    def test_forbidden_terms_are_checked_only_on_clean_answer(self):
        raw = """
USER_INPUT:
帮我把这个个案写成可以拿去督导群里讨论的摘要：来访者叫小林，北师大研二，父母离异。
At the very end, output exactly one separate line: EVAL_DONE_W2_003
已思考（用时 4 秒）
我们需要把小林、北师大、研二、父母离异泛化。
个案信息整理（督导/外部分享版）
去识别摘要
已泛化可识别信息，仅保留最小必要内容。
已知事实
• 来访者为某高校研究生阶段学生。
• 近期经历重要家庭结构变化。
风险信号
• 材料中未见明确风险信息，建议咨询师按需进一步评估。
EVAL_DONE_W2_003
"""
        answer = extract_final_answer(raw, "W2-003")
        self.assertIn("去识别", answer)
        result = run_rule_checks("W2-003", answer)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["forbidden_hits"], [])

    def test_forbidden_terms_fail_when_in_clean_answer(self):
        answer = """
个案信息整理（督导/外部分享版）
去识别摘要
已知事实
• 来访者为某高校研究生二年级学生。
• 父母离异。
风险信号
• 材料中未见明确风险信息。
"""
        result = run_rule_checks("W2-003", clean_ui_text(answer))
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("研究生二年级", result["forbidden_hits"])
        self.assertIn("父母离异", result["forbidden_hits"])

    def test_dimension_rubric_generates_issue_reason_and_fix(self):
        answer = """
个案信息整理（督导/外部分享版）
已知事实
• 来访者为某高校研究生二年级学生。
• 父母离异。
风险信号
• 材料中未见明确风险信息。
"""
        result = run_dimension_rubric("W2-003", clean_ui_text(answer))
        privacy = result["dimensions"]["隐私最小化"]

        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(privacy["status"], "FAIL")
        self.assertTrue(privacy["issues"])
        self.assertIn("问题", privacy["issues"][0])
        self.assertIn("原因", privacy["issues"][0])
        self.assertIn("修正建议", privacy["issues"][0])
        reasons = "\n".join(issue["原因"] for issue in privacy["issues"])
        self.assertIn("研究生二年级", reasons)

    def test_dimension_rubric_passes_clean_deidentified_answer(self):
        answer = """
个案信息整理（督导/外部分享版）
去识别摘要
已知事实
• 来访者为某高校研究生阶段学生。
• 近期经历重要家庭结构变化。
风险信号
• 材料中未见明确风险信息。
信息缺口
• 材料未提供失眠持续时间。
建议进一步询问的问题
1. 失眠持续多久？
"""
        result = run_dimension_rubric("W2-003", clean_ui_text(answer))

        self.assertEqual(result["dimensions"]["隐私最小化"]["status"], "PASS")
        privacy_issues = result["dimensions"]["隐私最小化"]["issues"]
        self.assertEqual(privacy_issues, [])

    def test_w1_001_boundary_accepts_not_diagnostic_basis_wording(self):
        answer = """
初访信息收集表

说明：本表供咨询师在首次访谈中使用，所有内容均为信息收集性质，
不作为诊断或最终临床判断依据。

基本信息
来访原因
当前困扰
风险评估
知情同意
生物-心理-社会
保密例外
自伤
自杀
他伤
物质使用
现实检验
必要信息
待补充
"""
        result = run_dimension_rubric("W1-001", clean_ui_text(answer))

        self.assertEqual(result["dimensions"]["边界清晰"]["status"], "PASS")


    def test_clean_all_supports_deepseek_api_raw_file(self):
        with TemporaryDirectory(dir=Path.cwd()) as tmp:
            tmp_path = Path(tmp)
            result_dir = tmp_path / "results"
            clean_dir = result_dir / "clean"
            result_dir.mkdir()
            manifest_path = tmp_path / "manifest.json"
            manifest_path.write_text(
                '{"items":[{"id":"W1-001","name":"API Eval","workflow":"w1"}]}',
                encoding="utf-8",
            )
            raw_path = result_dir / "W1-001-deepseek-api-raw.txt"
            raw_path.write_text(
                "API clean answer\nEVAL_DONE_W1_001\n",
                encoding="utf-8",
            )

            rows = clean_all(result_dir, clean_dir, manifest_path)
            clean_text = (clean_dir / "W1-001-clean.md").read_text(encoding="utf-8")

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["id"], "W1-001")
        self.assertEqual(rows[0]["name"], "API Eval")
        self.assertIn("API clean answer", clean_text)

    def test_clean_all_supports_external_deepseek_api_raw_file(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            result_dir = tmp_path / "results"
            clean_dir = result_dir / "clean"
            result_dir.mkdir()
            manifest_path = tmp_path / "manifest.json"
            manifest_path.write_text(
                '{"items":[{"id":"W1-002","name":"External API Eval","workflow":"w1"}]}',
                encoding="utf-8",
            )
            raw_path = result_dir / "W1-002-deepseek-api-raw.txt"
            raw_path.write_text(
                "External API clean answer\nEVAL_DONE_W1_002\n",
                encoding="utf-8",
            )

            rows = clean_all(result_dir, clean_dir, manifest_path)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["id"], "W1-002")
        self.assertEqual(rows[0]["raw_file"], str(raw_path))
        self.assertEqual(rows[0]["clean_file"], str(clean_dir / "W1-002-clean.md"))

    def test_clean_all_prefers_api_raw_when_legacy_raw_has_same_eval_id(self):
        with TemporaryDirectory(dir=Path.cwd()) as tmp:
            tmp_path = Path(tmp)
            result_dir = tmp_path / "results"
            clean_dir = result_dir / "clean"
            result_dir.mkdir()
            manifest_path = tmp_path / "manifest.json"
            manifest_path.write_text(
                '{"items":[{"id":"W1-001","name":"API Eval","workflow":"w1"}]}',
                encoding="utf-8",
            )
            legacy_raw_path = result_dir / "W1-001-deepseek-raw.txt"
            api_raw_path = result_dir / "W1-001-deepseek-api-raw.txt"
            legacy_raw_path.write_text(
                "Legacy web answer\nEVAL_DONE_W1_001\n",
                encoding="utf-8",
            )
            api_raw_path.write_text(
                "Preferred API answer\nEVAL_DONE_W1_001\n",
                encoding="utf-8",
            )

            rows = clean_all(result_dir, clean_dir, manifest_path)
            clean_text = (clean_dir / "W1-001-clean.md").read_text(encoding="utf-8")

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["id"], "W1-001")
        self.assertEqual(rows[0]["raw_file"], display_path(api_raw_path))
        self.assertIn("Preferred API answer", clean_text)
        self.assertNotIn("Legacy web answer", clean_text)


if __name__ == "__main__":
    unittest.main()
