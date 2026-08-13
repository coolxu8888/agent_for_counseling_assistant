import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from render_docx import WORD_NS, write_docx_package
from run_w2_template_acceptance import AcceptanceFailure, run_template_acceptance
from w2_acceptance import W2_REQUIRED_FIELDS, W2_TEMPLATE_PATH, validate_template_report


def template_xml():
    fields = [
        "Presenting concerns",
        "Case overview known facts",
        "Biological dimension known facts",
        "Protective factors",
        "Risk follow-up questions",
        "Recommended focus",
        "边界说明",
    ]
    body = "".join(f"<w:p><w:r><w:t>{field}: ____</w:t></w:r></w:p>" for field in fields)
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<w:document xmlns:w="{WORD_NS}"><w:body>{body}<w:sectPr/></w:body></w:document>'
    )


def structured_fixture():
    return {
        "workflow": "W2",
        "document_type": "case_summary",
        "deidentified": True,
        "title": "W2 BPS case background acceptance fixture",
        "presenting_concerns": ["W2 probe presenting concerns: insomnia and family pressure."],
        "case_overview": {
            "known_facts": ["W2 probe case overview: adult client with job stress."],
            "working_hypotheses": ["Stress overload may be maintaining sleep disruption."],
            "information_gaps": ["Support network details remain unclear."],
        },
        "bio_psycho_social": {
            "biological": {
                "known_facts": ["W2 probe biological: sleep worsened for two weeks."],
                "working_hypotheses": ["Fatigue may intensify emotional reactivity."],
                "information_gaps": ["Appetite and substance pattern need clarification."],
                "follow_up_questions": ["How many hours is the client sleeping most nights?"],
            },
            "psychological": {
                "known_facts": ["Anxiety about job performance is reported."],
                "working_hypotheses": ["Self-criticism may amplify distress."],
                "information_gaps": ["Automatic thoughts remain unclear."],
                "follow_up_questions": ["What thoughts appear after family conflict?"],
            },
            "social": {
                "known_facts": ["Family pressure is active."],
                "working_hypotheses": ["Reduced support may maintain distress."],
                "information_gaps": ["Peer support availability is unclear."],
                "follow_up_questions": ["Who can offer practical support this week?"],
            },
        },
        "protective_factors": ["W2 probe protective: help-seeking and continued work attendance."],
        "risk_formulation": {
            "observed_clues": ["Heavy drinking after conflict was reported."],
            "missing_or_unclear": ["Means access and escalation are not documented."],
            "follow_up_questions": ["W2 probe risk: ask about ideation, intent, plan, means, and support."],
        },
        "recommended_focus": ["W2 probe recommended focus: clarify timeline, support, and risk follow-up."],
        "boundary_notes": ["W2 probe boundary: this is not a diagnosis or final risk rating."],
    }


class W2TemplateAcceptanceTests(unittest.TestCase):
    def write_fixture_repo(self, root: Path) -> tuple[Path, Path]:
        template = root / W2_TEMPLATE_PATH
        structured = root / "eval-data" / "w2-bps-template-acceptance.json"
        write_docx_package(template, template_xml())
        structured.parent.mkdir(parents=True, exist_ok=True)
        structured.write_text(json.dumps(structured_fixture(), ensure_ascii=False, indent=2), encoding="utf-8")
        return template, structured

    def test_run_template_acceptance_fills_reopens_and_writes_sanitized_report(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            template, structured = self.write_fixture_repo(root)
            report = root / "eval-results" / "acceptance" / "w2" / "real-template.json"

            result = run_template_acceptance(template, structured, report, repo_root=root)

            validate_template_report(result, root)
            saved = json.loads(report.read_text(encoding="utf-8"))
            self.assertEqual(saved["workflow"], "W2")
            self.assertEqual(set(saved["fill"]["filled_fields"]), set(W2_REQUIRED_FIELDS))
            self.assertEqual(set(saved["output_verification"]["required_content"]), set(W2_REQUIRED_FIELDS))

    def test_run_template_acceptance_rejects_wrong_template_and_missing_reopen_content(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _template, structured = self.write_fixture_repo(root)
            wrong = root / "docs" / "wrong.docx"
            write_docx_package(wrong, template_xml())
            report = root / "eval-results" / "acceptance" / "w2" / "real-template.json"
            with self.assertRaisesRegex(AcceptanceFailure, "repository's real DOCX"):
                run_template_acceptance(wrong, structured, report, repo_root=root)

            template = root / W2_TEMPLATE_PATH

            def fake_fill(_template_path, _structured_path, output_path, _report_path):
                write_docx_package(output_path, template_xml())
                return {"status": "PASS", "filled_fields": [], "unfilled_fields": [], "issues": []}

            with self.assertRaisesRegex(AcceptanceFailure, "missing canonical W2 content"):
                run_template_acceptance(template, structured, report, repo_root=root, fill_helper=fake_fill)

    def test_real_repo_template_fixture_is_a_valid_docx_when_present(self):
        root = Path(__file__).resolve().parents[1]
        template = root / W2_TEMPLATE_PATH
        if template.exists():
            self.assertTrue(zipfile.is_zipfile(template))


if __name__ == "__main__":
    unittest.main()
