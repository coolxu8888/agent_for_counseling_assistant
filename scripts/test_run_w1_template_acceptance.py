import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from run_w1_template_acceptance import (
    AcceptanceFailure,
    inspect_template,
    run_template_acceptance,
)
from w1_acceptance import W1_SUMMARY_SECTIONS, validate_template_report


WORD_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
TEMPLATE_NAME = "4.\u5fc3\u7406\u54a8\u8be2\u521d\u59cb\u8bbf\u8c08\u8868_20210906.docx"


def write_docx(path: Path, paragraphs: list[str]) -> None:
    body = "".join(
        f"<w:p><w:r><w:t>{text}</w:t></w:r></w:p>" for text in paragraphs
    )
    document = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<w:document xmlns:w="{WORD_NS}"><w:body>{body}<w:sectPr/></w:body></w:document>'
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as package:
        package.writestr("word/document.xml", document)


def structured_result() -> dict:
    return {
        "workflow": "W1",
        "document_type": "initial_session_summary",
        "deidentified": True,
        "sections": [
            {
                "id": section_id,
                "heading": section_id,
                "known_facts": [f"verified-{section_id}"],
                "unclear_or_missing": [f"missing-{section_id}"],
                "follow_up_questions": [f"question-{section_id}"],
            }
            for section_id in W1_SUMMARY_SECTIONS
        ],
    }


class W1TemplateAcceptanceTests(unittest.TestCase):
    def test_inspect_template_rejects_raw_xml_fixture(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            xml = root / "docs" / "template.xml"
            xml.parent.mkdir()
            xml.write_text("<w:document/>", encoding="utf-8")
            with self.assertRaisesRegex(AcceptanceFailure, "real DOCX"):
                inspect_template(xml, root)

    def test_real_template_run_invokes_filler_reopens_and_validates_all_sections(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            template = root / "docs" / TEMPLATE_NAME
            structured = root / "fixture.json"
            report = root / "eval-results" / "acceptance" / "w1" / "real-template.json"
            write_docx(template, [f"{section_id}:" for section_id in W1_SUMMARY_SECTIONS])
            structured.write_text(json.dumps(structured_result()), encoding="utf-8")
            calls = []

            from fill_docx_template import fill_docx_template

            def recording_filler(*args, **kwargs):
                calls.append(args)
                return fill_docx_template(*args, **kwargs)

            result = run_template_acceptance(
                template, structured, report, repo_root=root, fill_helper=recording_filler
            )

            self.assertEqual(len(calls), 1)
            self.assertEqual(result["output_verification"]["status"], "PASS")
            self.assertEqual(
                set(result["fill"]["filled_fields"]), set(W1_SUMMARY_SECTIONS)
            )
            validate_template_report(json.loads(report.read_text(encoding="utf-8")), root)
            self.assertEqual(list(report.parent.glob("*.docx")), [])

    def test_run_refuses_missing_canonical_section_before_filling(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            template = root / "docs" / TEMPLATE_NAME
            structured = root / "fixture.json"
            report = root / "eval-results" / "acceptance" / "w1" / "real-template.json"
            write_docx(template, ["main_distress:"])
            data = structured_result()
            data["sections"].pop()
            structured.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaisesRegex(AcceptanceFailure, "canonical"):
                run_template_acceptance(template, structured, report, repo_root=root)
            self.assertFalse(report.exists())

    def test_run_refuses_report_outside_acceptance_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            template = root / "docs" / TEMPLATE_NAME
            structured = root / "fixture.json"
            write_docx(template, [f"{section_id}:" for section_id in W1_SUMMARY_SECTIONS])
            structured.write_text(json.dumps(structured_result()), encoding="utf-8")
            with self.assertRaisesRegex(AcceptanceFailure, "acceptance/w1"):
                run_template_acceptance(
                    template, structured, root / "unsafe-report.json", repo_root=root
                )


if __name__ == "__main__":
    unittest.main()
