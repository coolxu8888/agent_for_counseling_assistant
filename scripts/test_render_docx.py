import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from render_docx import render_docx


class RenderDocxTest(unittest.TestCase):
    def minimal_w3(self):
        return {
            "workflow": "W3",
            "document_type": "session_note",
            "title": "本次咨询记录",
            "sections": [
                {"heading": "本次主题", "content": "主题"},
                {"heading": "风险变化", "content": "材料中未提供风险相关信息"},
            ],
            "risk_change": {"content": "材料中未提供风险相关信息"},
            "next_session_focus": ["继续讨论表达方式"],
            "missing_information": ["来访者状态未提供"],
            "boundary_notes": ["本记录不替代咨询师专业判断。"],
        }

    def read_document_xml(self, docx_path):
        with zipfile.ZipFile(docx_path) as package:
            return package.read("word/document.xml").decode("utf-8")

    def test_render_docx_creates_minimal_ooxml_package(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_path = Path(tmp) / "output.docx"

            check = render_docx(self.minimal_w3(), output_path)

            with zipfile.ZipFile(output_path) as package:
                names = set(package.namelist())

        self.assertEqual(check["status"], "PASS")
        self.assertIn("[Content_Types].xml", names)
        self.assertIn("_rels/.rels", names)
        self.assertIn("word/document.xml", names)
        self.assertIn("word/styles.xml", names)


if __name__ == "__main__":
    unittest.main()
