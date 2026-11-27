import io
import json
import tempfile
import unittest
import zipfile
from functools import partial
from pathlib import Path
from unittest.mock import Mock, patch
from xml.etree import ElementTree

import web_workbench
from render_docx import WORD_NS
from run_agent import run_agent_once
from run_model_eval import DeepSeekConfig
from workbench_store import WorkbenchStore


def docx_paragraphs(docx_bytes):
    with zipfile.ZipFile(io.BytesIO(docx_bytes)) as package:
        root = ElementTree.fromstring(package.read("word/document.xml"))
    ns = {"w": WORD_NS}
    return ["".join(p.itertext()) for p in root.findall("./w:body/w:p", ns)]


class IntakeProductExportTest(unittest.TestCase):
    def test_auto_intake_generates_and_reexports_the_complete_word_document(self):
        questions = [
            "你想先写下哪些内容？ English: What would you like to write down first?",
            "哪些问题想留到后面？ English: What questions would you prefer to discuss later?",
            "感到不安时可以向谁求助？ English: Who could you reach out to if you feel uneasy?",
        ]
        clue = {
            "id": "C1",
            "content": "偏好书面表达 & 阅读 <交流前>。",
            "source": "合成预约问卷",
            "source_type": "questionnaire",
            "status": "reported",
        }
        data = {
            "workflow": "W1",
            "document_type": "intake_form",
            "title": "合成首访准备材料",
            "sections": [
                {
                    "heading": "交流偏好",
                    "fields": [{
                        "label": "表达方式",
                        "value": clue["content"],
                        "notes": "先确认书面沟通是否合适。",
                        "required": True,
                        "sensitive": False,
                        "risk_signal": False,
                        "suggested_questions": questions[:2],
                        "known_clues_used": ["C1"],
                    }],
                },
                {
                    "heading": "风险评估",
                    "content": "可联系的支持对象待核实。",
                    "fields": [{
                        "label": "支持对象",
                        "value": "",
                        "required": False,
                        "sensitive": True,
                        "risk_signal": True,
                        "suggested_questions": questions[2:],
                    }],
                },
            ],
            "boundary_notes": ["会谈开始前确认保密范围。"],
            "known_clues": [clue],
        }
        markdown_body = "\n".join(["# " + data["title"], "", *("- " + q for q in questions)])
        answer = (
            f"{markdown_body}\n\n```json\n"
            f"{json.dumps(data, ensure_ascii=False)}\n```\nAGENT_DONE_W1\n"
        )
        fake_post = Mock(return_value={
            "choices": [{"message": {"content": answer}, "finish_reason": "stop"}],
        })

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_root = root / "runs"
            store = WorkbenchStore(root / "test.sqlite3", root / "uploads")
            user = store.create_user("test-counselor", "synthetic-test-password")
            test_runner = partial(
                run_agent_once,
                run_root=run_root,
                config=DeepSeekConfig(api_key="test-key", base_url="https://model.example.test"),
                http_post_json=fake_post,
            )
            with (
                patch.object(web_workbench, "RUN_ROOT", run_root),
                patch.object(web_workbench, "RUN_LOG_PATH", root / "run-log.jsonl"),
                patch.object(web_workbench, "STORE", store),
                patch.object(web_workbench, "run_agent_once", test_runner),
            ):
                status, _, body = web_workbench.handle_api_run({
                    "user_id": user["id"],
                    "workflow": "AUTO",
                    "input": "首次访谈前，请准备初访提问提纲和可编辑的 Word 文档。合成线索：偏好用书面方式表达。",
                })
                payload = json.loads(body)
                self.assertEqual(status, 200, payload)
                self.assertEqual(payload["status"], "success", payload.get("metadata"))
                self.assertEqual(payload["detected_workflow"], "W1")
                self.assertEqual(payload["w1_mode"], "intake_prep")
                self.assertEqual(payload["docx"]["status"], "PASS")
                self.assertEqual(payload["structured_output"]["known_clues"], [clue])
                self.assertIn(clue["source"], payload["workflow_mode_notice"])
                self.assertEqual(payload["clean_output"].strip(), markdown_body)

                status, _, generated_bytes = web_workbench.handle_file_download(
                    payload["docx"]["download_url"], user=user
                )
                self.assertEqual(status, 200)
                generated = docx_paragraphs(generated_bytes)
                output_path = Path(payload["docx"]["path"])
                self.assertTrue(output_path.resolve().is_relative_to(run_root.resolve()))
                output_path.unlink()
                status, _, body = web_workbench.handle_render_docx({
                    "user_id": user["id"], "run_dir": payload["run_dir"],
                })
                rerendered = json.loads(body)
                self.assertEqual(status, 200, rerendered)
                self.assertEqual(rerendered["check"]["status"], "PASS")
                self.assertEqual(docx_paragraphs(Path(rerendered["output_path"]).read_bytes()), generated)

        fake_post.assert_called_once()
        self.assertEqual(fake_post.call_args.args[2]["max_tokens"], 32768)
        self.assertEqual(payload["metadata"]["max_tokens"], 32768)
        self.assertEqual([p.partition(". ")[2] for p in generated if " English: " in p], questions)
        text = "\n".join(generated)
        for marker in ("必填", "敏感", "风险信号", "状态", "reported"):
            self.assertNotIn(marker, text)
        self.assertIn("使用的已知线索：C1", text)
        self.assertIn("可联系的支持对象待核实。", text)
        self.assertLess(text.index("风险评估"), text.index("边界说明"))
        self.assertLess(text.index("边界说明"), text.index("已提供线索"))
        self.assertTrue(generated[-1].startswith("C1：" + clue["content"]))
        self.assertIn("来源：" + clue["source"], generated[-1])


if __name__ == "__main__":
    unittest.main()
