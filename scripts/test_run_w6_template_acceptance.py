import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from render_docx import WORD_NS, write_docx_package
from run_w6_template_acceptance import AcceptanceFailure, run_template_acceptance
from w6_acceptance import W6_REQUIRED_FIELDS, W6_TEMPLATE_PATH, validate_template_report


def template_xml():
    fields = [
        "Selected framework",
        "Overview",
        "Phases",
        "Hypotheses to verify",
        "Session focus options",
        "Risk monitoring checkpoints",
        "Collaboration or referral reminders",
        "Missing information",
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
        "workflow": "W6",
        "document_type": "counseling_roadmap",
        "deidentified": True,
        "title": "W6 counseling roadmap acceptance fixture",
        "selected_framework": "INTEGRATIVE",
        "overview": ["W6 probe overview: bounded and revisable counseling roadmap."],
        "phases": ["W6 probe phases: engagement, hypothesis testing, consolidation."],
        "hypotheses_to_verify": ["W6 probe hypothesis: criticism may activate shame and avoidance."],
        "session_focus_options": ["W6 probe focus: clarify the latest criticism trigger."],
        "risk_monitoring_checkpoints": ["W6 probe risk: re-check ideation, self-harm, sleep, and supports."],
        "collaboration_or_referral_reminders": ["W6 probe referral: consider collaboration only for new safety or medical concerns."],
        "missing_information": ["W6 probe missing: prior counseling response is not documented."],
        "do_not_do": ["W6 probe do-not-do: do not diagnose, promise outcomes, or prescribe a fixed protocol."],
        "boundary_notes": ["W6 probe boundary: roadmap only, adjusted by counselor judgment."],
    }


class W6TemplateAcceptanceTests(unittest.TestCase):
    def write_fixture_repo(self, root: Path) -> tuple[Path, Path]:
        template = root / W6_TEMPLATE_PATH
        structured = root / "eval-data" / "w6-roadmap-template-acceptance.json"
        write_docx_package(template, template_xml())
        structured.parent.mkdir(parents=True, exist_ok=True)
        structured.write_text(json.dumps(structured_fixture(), ensure_ascii=False, indent=2), encoding="utf-8")
        return template, structured

    def test_run_template_acceptance_fills_reopens_and_writes_sanitized_report(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            template, structured = self.write_fixture_repo(root)
            report = root / "eval-results" / "acceptance" / "w6" / "real-template.json"

            result = run_template_acceptance(template, structured, report, repo_root=root)

            validate_template_report(result, root)
            saved = json.loads(report.read_text(encoding="utf-8"))
            self.assertEqual(saved["workflow"], "W6")
            self.assertEqual(set(saved["fill"]["filled_fields"]), set(W6_REQUIRED_FIELDS))
            self.assertEqual(set(saved["output_verification"]["required_content"]), set(W6_REQUIRED_FIELDS))

    def test_run_template_acceptance_rejects_wrong_template_and_missing_reopen_content(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _template, structured = self.write_fixture_repo(root)
            wrong = root / "docs" / "wrong.docx"
            write_docx_package(wrong, template_xml())
            report = root / "eval-results" / "acceptance" / "w6" / "real-template.json"
            with self.assertRaisesRegex(AcceptanceFailure, "repository's real DOCX"):
                run_template_acceptance(wrong, structured, report, repo_root=root)

            template = root / W6_TEMPLATE_PATH

            def fake_fill(_template_path, _structured_path, output_path, _report_path):
                write_docx_package(output_path, template_xml())
                return {"status": "PASS", "filled_fields": [], "unfilled_fields": [], "issues": []}

            with self.assertRaisesRegex(AcceptanceFailure, "missing canonical W6 content"):
                run_template_acceptance(template, structured, report, repo_root=root, fill_helper=fake_fill)

    def test_real_repo_template_fixture_is_a_valid_docx_when_present(self):
        root = Path(__file__).resolve().parents[1]
        template = root / W6_TEMPLATE_PATH
        if template.exists():
            self.assertTrue(zipfile.is_zipfile(template))


if __name__ == "__main__":
    unittest.main()
