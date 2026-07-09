import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from render_docx import WORD_NS, write_docx_package
from run_w3_template_acceptance import AcceptanceFailure, run_template_acceptance
from w3_acceptance import W3_REQUIRED_FIELDS, W3_TEMPLATE_PATH, validate_template_report


def template_xml():
    fields = [
        "Record format",
        "Subjective",
        "Objective",
        "Assessment",
        "Plan",
        "Risk change documentation",
        "Risk follow-up actions",
        "Next session focus",
        "边界说明",
    ]
    body = "".join(f"<w:p><w:r><w:t>{field}: ____</w:t></w:r></w:p>" for field in fields)
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<w:document xmlns:w="{WORD_NS}"><w:body>{body}<w:sectPr/></w:body></w:document>'
    )


def structured_fixture():
    return {
        "workflow": "W3",
        "document_type": "session_note",
        "deidentified": True,
        "title": "W3 SOAP counseling-record acceptance fixture",
        "record_format": "SOAP",
        "sections": [
            {
                "id": "subjective",
                "heading": "Subjective",
                "content": "W3 probe subjective: client reported panic decreased compared with last week.",
            },
            {
                "id": "objective",
                "heading": "Objective",
                "content": "W3 probe objective: counselor observed steadier breathing after grounding practice.",
            },
            {
                "id": "assessment",
                "heading": "Assessment",
                "content": "W3 probe assessment: distress appears reduced while family conflict remains a trigger.",
            },
            {
                "id": "plan",
                "heading": "Plan",
                "content": "W3 probe plan: continue grounding practice and review support options.",
            },
        ],
        "risk_change": {
            "content": "Client denied current intent or plan in this de-identified note.",
            "change_documentation": "W3 probe risk change: panic intensity decreased from last week.",
            "follow_up_actions": ["W3 probe risk follow-up: recheck ideation, intent, plan, means, and supports."],
        },
        "next_session_focus": ["W3 probe next focus: review grounding and family-boundary stressors."],
        "boundary_notes": ["W3 probe boundary: this record documents provided material only and is not a diagnosis."],
    }


class W3TemplateAcceptanceTests(unittest.TestCase):
    def write_fixture_repo(self, root: Path) -> tuple[Path, Path]:
        template = root / W3_TEMPLATE_PATH
        structured = root / "eval-data" / "w3-session-note-template-acceptance.json"
        write_docx_package(template, template_xml())
        structured.parent.mkdir(parents=True, exist_ok=True)
        structured.write_text(json.dumps(structured_fixture(), ensure_ascii=False, indent=2), encoding="utf-8")
        return template, structured

    def test_run_template_acceptance_fills_reopens_and_writes_sanitized_report(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            template, structured = self.write_fixture_repo(root)
            report = root / "eval-results" / "acceptance" / "w3" / "real-template.json"

            result = run_template_acceptance(template, structured, report, repo_root=root)

            validate_template_report(result, root)
            saved = json.loads(report.read_text(encoding="utf-8"))
            self.assertEqual(saved["workflow"], "W3")
            self.assertEqual(set(saved["fill"]["filled_fields"]), set(W3_REQUIRED_FIELDS))
            self.assertEqual(set(saved["output_verification"]["required_content"]), set(W3_REQUIRED_FIELDS))

    def test_run_template_acceptance_rejects_wrong_template_and_missing_reopen_content(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _template, structured = self.write_fixture_repo(root)
            wrong = root / "docs" / "wrong.docx"
            write_docx_package(wrong, template_xml())
            report = root / "eval-results" / "acceptance" / "w3" / "real-template.json"
            with self.assertRaisesRegex(AcceptanceFailure, "repository's real DOCX"):
                run_template_acceptance(wrong, structured, report, repo_root=root)

            template = root / W3_TEMPLATE_PATH

            def fake_fill(_template_path, _structured_path, output_path, _report_path):
                write_docx_package(output_path, template_xml())
                return {"status": "PASS", "filled_fields": [], "unfilled_fields": [], "issues": []}

            with self.assertRaisesRegex(AcceptanceFailure, "missing canonical W3 content"):
                run_template_acceptance(template, structured, report, repo_root=root, fill_helper=fake_fill)

    def test_real_repo_template_fixture_is_a_valid_docx_when_present(self):
        root = Path(__file__).resolve().parents[1]
        template = root / W3_TEMPLATE_PATH
        if template.exists():
            self.assertTrue(zipfile.is_zipfile(template))


if __name__ == "__main__":
    unittest.main()
