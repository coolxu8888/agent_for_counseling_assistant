import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from render_docx import WORD_NS, write_docx_package
from run_w4_template_acceptance import AcceptanceFailure, run_template_acceptance
from w4_acceptance import W4_REQUIRED_FIELDS, W4_TEMPLATE_PATH, validate_template_report


def template_xml():
    fields = [
        "Selected framework",
        "Known facts",
        "Presenting patterns",
        "Predisposing factors",
        "Precipitating factors",
        "Maintaining factors",
        "Protective factors",
        "Risk considerations",
        "Working hypotheses",
        "Questions to verify",
        "Boundary notes",
    ]
    body = "".join(f"<w:p><w:r><w:t>{field}: ____</w:t></w:r></w:p>" for field in fields)
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<w:document xmlns:w="{WORD_NS}"><w:body>{body}<w:sectPr/></w:body></w:document>'
    )


def structured_fixture():
    return {
        "workflow": "W4",
        "document_type": "case_conceptualization",
        "deidentified": True,
        "title": "W4 CBT case conceptualization acceptance fixture",
        "selected_framework": "CBT",
        "known_facts": ["W4 probe known facts: client becomes anxious before performance reviews."],
        "presenting_patterns": ["W4 probe presenting pattern: criticism-anxiety-avoidance cycle."],
        "predisposing_factors": ["W4 probe predisposing: family comparison history."],
        "precipitating_factors": ["W4 probe precipitating: recent supervisor conflict."],
        "maintaining_factors": ["W4 probe maintaining: avoidance reduces corrective feedback."],
        "protective_factors": ["W4 probe protective: help-seeking and no reported suicide plan."],
        "risk_considerations": ["W4 probe risk: continue checking ideation, intent, plan, means, and support."],
        "working_hypotheses": ["W4 probe hypothesis: performance evaluation activates inadequacy beliefs."],
        "questions_to_verify": ["W4 probe question: what evidence supports predicted criticism?"],
        "boundary_notes": ["W4 probe boundary: working hypothesis, not diagnosis or treatment plan."],
    }


class W4TemplateAcceptanceTests(unittest.TestCase):
    def write_fixture_repo(self, root: Path) -> tuple[Path, Path]:
        template = root / W4_TEMPLATE_PATH
        structured = root / "eval-data" / "w4-conceptualization-template-acceptance.json"
        write_docx_package(template, template_xml())
        structured.parent.mkdir(parents=True, exist_ok=True)
        structured.write_text(json.dumps(structured_fixture(), ensure_ascii=False, indent=2), encoding="utf-8")
        return template, structured

    def test_run_template_acceptance_fills_reopens_and_writes_sanitized_report(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            template, structured = self.write_fixture_repo(root)
            report = root / "eval-results" / "acceptance" / "w4" / "real-template.json"

            result = run_template_acceptance(template, structured, report, repo_root=root)

            validate_template_report(result, root)
            saved = json.loads(report.read_text(encoding="utf-8"))
            self.assertEqual(saved["workflow"], "W4")
            self.assertEqual(set(saved["fill"]["filled_fields"]), set(W4_REQUIRED_FIELDS))
            self.assertEqual(set(saved["output_verification"]["required_content"]), set(W4_REQUIRED_FIELDS))

    def test_run_template_acceptance_rejects_wrong_template_and_missing_reopen_content(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _template, structured = self.write_fixture_repo(root)
            wrong = root / "docs" / "wrong.docx"
            write_docx_package(wrong, template_xml())
            report = root / "eval-results" / "acceptance" / "w4" / "real-template.json"
            with self.assertRaisesRegex(AcceptanceFailure, "repository's real DOCX"):
                run_template_acceptance(wrong, structured, report, repo_root=root)

            template = root / W4_TEMPLATE_PATH

            def fake_fill(_template_path, _structured_path, output_path, _report_path):
                write_docx_package(output_path, template_xml())
                return {"status": "PASS", "filled_fields": [], "unfilled_fields": [], "issues": []}

            with self.assertRaisesRegex(AcceptanceFailure, "missing canonical W4 content"):
                run_template_acceptance(template, structured, report, repo_root=root, fill_helper=fake_fill)

    def test_real_repo_template_fixture_is_a_valid_docx_when_present(self):
        root = Path(__file__).resolve().parents[1]
        template = root / W4_TEMPLATE_PATH
        if template.exists():
            self.assertTrue(zipfile.is_zipfile(template))


if __name__ == "__main__":
    unittest.main()
