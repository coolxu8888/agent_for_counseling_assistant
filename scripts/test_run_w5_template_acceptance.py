import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from render_docx import WORD_NS, write_docx_package
from run_w5_template_acceptance import AcceptanceFailure, run_template_acceptance
from w5_acceptance import W5_REQUIRED_FIELDS, W5_TEMPLATE_PATH, validate_template_report


def template_xml():
    fields = [
        "Selected framework",
        "Session goal",
        "Focus areas",
        "Planned interventions",
        "Suggested questions",
        "Risk monitoring",
        "Between-session tasks",
        "Do not do",
        "Boundary notes",
    ]
    body = "".join(f"<w:p><w:r><w:t>{field}: ____</w:t></w:r></w:p>" for field in fields)
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<w:document xmlns:w="{WORD_NS}"><w:body>{body}<w:sectPr/></w:body></w:document>'
    )


def structured_fixture():
    return {
        "workflow": "W5",
        "document_type": "next_session_plan",
        "deidentified": True,
        "title": "W5 next-session plan acceptance fixture",
        "selected_framework": "CBT",
        "session_goal": ["W5 probe session goal: explore the criticism-anxiety-avoidance loop in one next session."],
        "focus_areas": ["W5 probe focus: automatic thoughts, avoidance behavior, anxiety intensity, and risk check."],
        "planned_interventions": ["W5 probe intervention: use Socratic questions and a brief thought record."],
        "suggested_questions": ["W5 probe question: what sentence appears first when you imagine feedback?"],
        "risk_monitoring": ["W5 probe risk: re-check ideation, self-harm, sleep deterioration, and available support."],
        "between_session_tasks": ["W5 probe task: optionally record one trigger, thought, and emotion rating."],
        "do_not_do": ["W5 probe do-not-do: do not diagnose, write a roadmap, or replace counselor judgment."],
        "boundary_notes": ["W5 probe boundary: single next-session plan only, adjusted by counselor judgment."],
    }


class W5TemplateAcceptanceTests(unittest.TestCase):
    def write_fixture_repo(self, root: Path) -> tuple[Path, Path]:
        template = root / W5_TEMPLATE_PATH
        structured = root / "eval-data" / "w5-next-session-template-acceptance.json"
        write_docx_package(template, template_xml())
        structured.parent.mkdir(parents=True, exist_ok=True)
        structured.write_text(json.dumps(structured_fixture(), ensure_ascii=False, indent=2), encoding="utf-8")
        return template, structured

    def test_run_template_acceptance_fills_reopens_and_writes_sanitized_report(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            template, structured = self.write_fixture_repo(root)
            report = root / "eval-results" / "acceptance" / "w5" / "real-template.json"

            result = run_template_acceptance(template, structured, report, repo_root=root)

            validate_template_report(result, root)
            saved = json.loads(report.read_text(encoding="utf-8"))
            self.assertEqual(saved["workflow"], "W5")
            self.assertEqual(set(saved["fill"]["filled_fields"]), set(W5_REQUIRED_FIELDS))
            self.assertEqual(set(saved["output_verification"]["required_content"]), set(W5_REQUIRED_FIELDS))

    def test_run_template_acceptance_rejects_wrong_template_and_missing_reopen_content(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _template, structured = self.write_fixture_repo(root)
            wrong = root / "docs" / "wrong.docx"
            write_docx_package(wrong, template_xml())
            report = root / "eval-results" / "acceptance" / "w5" / "real-template.json"
            with self.assertRaisesRegex(AcceptanceFailure, "repository's real DOCX"):
                run_template_acceptance(wrong, structured, report, repo_root=root)

            template = root / W5_TEMPLATE_PATH

            def fake_fill(_template_path, _structured_path, output_path, _report_path):
                write_docx_package(output_path, template_xml())
                return {"status": "PASS", "filled_fields": [], "unfilled_fields": [], "issues": []}

            with self.assertRaisesRegex(AcceptanceFailure, "missing canonical W5 content"):
                run_template_acceptance(template, structured, report, repo_root=root, fill_helper=fake_fill)

    def test_real_repo_template_fixture_is_a_valid_docx_when_present(self):
        root = Path(__file__).resolve().parents[1]
        template = root / W5_TEMPLATE_PATH
        if template.exists():
            self.assertTrue(zipfile.is_zipfile(template))


if __name__ == "__main__":
    unittest.main()
