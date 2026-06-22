import json
import tempfile
import unittest
from pathlib import Path

from run_model_eval import DeepSeekConfig
from run_template_fill_eval import load_template_fill_eval_items, run_single_template_fill_eval


class RunTemplateFillEvalTest(unittest.TestCase):
    def test_load_template_fill_eval_items_resolves_relative_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = root / "template-fill-manifest.json"
            manifest_path.write_text(
                json.dumps(
                    [
                        {
                            "id": "TF-TEST",
                            "template_xml_file": "fixtures/template.xml",
                            "structured_output_file": "fixtures/structured.json",
                            "expected_source_path": "next_session_focus",
                        }
                    ],
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            fixtures = root / "fixtures"
            fixtures.mkdir()
            (fixtures / "template.xml").write_text("<xml />", encoding="utf-8")
            (fixtures / "structured.json").write_text("{}", encoding="utf-8")

            items = load_template_fill_eval_items(manifest_path)

        self.assertTrue(items[0]["template_xml_file"].endswith("fixtures\\template.xml"))
        self.assertTrue(items[0]["structured_output_file"].endswith("fixtures\\structured.json"))

    def test_run_single_template_fill_eval_scores_llm_mapping_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            template_xml = root / "template.xml"
            structured_output = root / "structured.json"
            result_dir = root / "results"
            template_xml.write_text(
                """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p><w:r><w:t>咨询目标：____</w:t></w:r></w:p>
    <w:sectPr />
  </w:body>
</w:document>
""",
                encoding="utf-8",
            )
            structured_output.write_text(
                json.dumps(
                    {
                        "workflow": "W3",
                        "document_type": "session_note",
                        "title": "Session note",
                        "sections": [{"heading": "主题", "content": "Discussed panic and presentation worry."}],
                        "risk_change": {"content": "No new escalation was documented."},
                        "next_session_focus": ["Review the presentation outcome and coping follow-through."],
                        "missing_information": ["No direct counselor observation was documented."],
                        "boundary_notes": ["Counselor-facing only."],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            item = {
                "id": "TF-TEST",
                "name": "template-llm-mapping",
                "template_xml_file": str(template_xml),
                "structured_output_file": str(structured_output),
                "expected_source_path": "next_session_focus",
                "expected_label": "咨询目标",
                "expected_output_contains": ["Review the presentation outcome"],
            }

            def fake_post(url, headers, payload, timeout):
                return {
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps(
                                    {
                                        "mappings": [
                                            {
                                                "slot_id": "paragraph[0]",
                                                "template_label": "咨询目标",
                                                "source_path": "next_session_focus",
                                                "confidence": "medium",
                                                "reason": "Forward-looking target field.",
                                            }
                                        ]
                                    }
                                )
                            }
                        }
                    ]
                }

            result = run_single_template_fill_eval(
                item,
                DeepSeekConfig(api_key="test-key", model="deepseek-v4-flash", base_url="https://example.test"),
                result_dir,
                http_post_json=fake_post,
            )

        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["report"]["llm_status"], "success")
        self.assertEqual(result["mapping"]["mappings"][0]["source_path"], "next_session_focus")


if __name__ == "__main__":
    unittest.main()
