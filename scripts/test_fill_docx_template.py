import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from fill_docx_template import (
    build_source_map,
    build_source_paths,
    build_template_mapping,
    build_llm_mapping_prompt,
    extract_template_slots_from_xml,
    extract_llm_mapping_json,
    fill_docx_template,
    find_source_match,
    merge_template_mappings,
    main,
    normalize_label,
    parse_args,
    run_deepseek_template_mapping,
    unresolved_mapping_items,
    validate_llm_mapping,
)
from run_model_eval import DeepSeekConfig
from render_docx import WORD_NS, write_docx_package


class FillDocxTemplateTest(unittest.TestCase):
    def sample_w3(self):
        return {
            "workflow": "W3",
            "document_type": "session_note",
            "title": "本次咨询记录",
            "sections": [
                {"heading": "本次主题", "content": "讨论分手后的低落情绪。"},
                {"heading": "咨询师干预", "content": "支持性回应并讨论社会支持。"},
            ],
            "risk_change": {"content": "出现被动自杀意念，无具体计划。"},
            "next_session_focus": ["继续评估安全情况", "回顾联系朋友的结果"],
            "missing_information": ["风险意念频率与强度"],
            "boundary_notes": ["本记录不替代正式风险评估。"],
        }

    def test_normalize_label_removes_punctuation_and_placeholders(self):
        self.assertEqual(normalize_label(" 风险变化：____ "), "风险变化")

    def test_build_source_map_exposes_w3_core_fields(self):
        source_map = build_source_map(self.sample_w3())

        match = find_source_match("风险变化", source_map)

        self.assertIsNotNone(match)
        self.assertEqual(match["source_path"], "risk_change.content")
        self.assertEqual(match["value"], "出现被动自杀意念，无具体计划。")

    def test_find_source_match_supports_medium_contains_match(self):
        source_map = build_source_map(self.sample_w3())

        match = find_source_match("下次咨询重点安排", source_map)

        self.assertIsNotNone(match)
        self.assertEqual(match["confidence"], "medium")
        self.assertIn("继续评估安全情况", match["value"])

    def test_extract_template_slots_from_xml_finds_table_and_paragraph_slots(self):
        slots = extract_template_slots_from_xml(self.template_xml())

        self.assertEqual(slots[0]["slot_id"], "table[0].row[0].cell[1]")
        self.assertEqual(slots[0]["label"], "风险变化")
        self.assertEqual(slots[0]["slot_type"], "table_adjacent_cell")
        self.assertEqual(slots[0]["current_text"], "____")
        self.assertEqual(slots[1]["slot_id"], "paragraph[0]")
        self.assertEqual(slots[1]["label"], "下次咨询重点")
        self.assertEqual(slots[1]["slot_type"], "paragraph_placeholder")

    def test_build_source_paths_exports_structured_values(self):
        source_paths = build_source_paths(self.sample_w3())

        paths = [item["source_path"] for item in source_paths]

        self.assertIn("risk_change.content", paths)
        self.assertIn("next_session_focus", paths)

    def test_build_template_mapping_maps_known_slots_to_source_paths(self):
        slots = extract_template_slots_from_xml(self.template_xml())
        source_paths = build_source_paths(self.sample_w3())

        mapping = build_template_mapping(slots, source_paths)

        self.assertEqual(mapping["mappings"][0]["slot_id"], "table[0].row[0].cell[1]")
        self.assertEqual(mapping["mappings"][0]["source_path"], "risk_change.content")
        self.assertEqual(mapping["mappings"][0]["fill_status"], "ready")
        self.assertEqual(mapping["mappings"][1]["slot_id"], "paragraph[0]")
        self.assertEqual(mapping["mappings"][1]["source_path"], "next_session_focus")
        self.assertEqual(mapping["mappings"][1]["fill_status"], "ready")

    def test_build_template_mapping_marks_unknown_slots_unmapped(self):
        slots = extract_template_slots_from_xml(self.unknown_placeholder_xml())
        source_paths = build_source_paths(self.sample_w3())

        mapping = build_template_mapping(slots, source_paths)

        self.assertEqual(mapping["mappings"][0]["source_path"], "unmapped")
        self.assertEqual(mapping["mappings"][0]["confidence"], "none")
        self.assertEqual(mapping["mappings"][0]["fill_status"], "skipped")

    def test_build_llm_mapping_prompt_constrains_model_to_json_and_source_paths(self):
        slots = extract_template_slots_from_xml(self.unknown_placeholder_xml())
        source_paths = build_source_paths(self.sample_w3())

        prompt = build_llm_mapping_prompt(slots, source_paths)

        self.assertIn("JSON only", prompt)
        self.assertIn("source_path", prompt)
        self.assertIn("unmapped", prompt)
        self.assertIn("risk_change.content", prompt)

    def test_extract_llm_mapping_json_accepts_fenced_json(self):
        answer = (
            "```json\n"
            "{\"mappings\":[{\"slot_id\":\"paragraph[0]\",\"template_label\":\"x\","
            "\"source_path\":\"risk_change.content\",\"confidence\":\"medium\",\"reason\":\"match\"}]}"
            "\n```"
        )

        mapping = extract_llm_mapping_json(answer)

        self.assertEqual(mapping["mappings"][0]["source_path"], "risk_change.content")

    def test_validate_llm_mapping_accepts_known_source_paths(self):
        requested_slot_ids = {"paragraph[0]"}
        allowed_source_paths = {"risk_change.content", "next_session_focus"}
        llm_mapping = {
            "mappings": [
                {
                    "slot_id": "paragraph[0]",
                    "template_label": "鍜ㄨ鐩爣",
                    "source_path": "risk_change.content",
                    "confidence": "medium",
                    "reason": "closest safe match",
                }
            ]
        }

        validated = validate_llm_mapping(llm_mapping, requested_slot_ids, allowed_source_paths)

        self.assertEqual(validated["mappings"][0]["source_path"], "risk_change.content")
        self.assertEqual(validated["mappings"][0]["fill_status"], "ready")

    def test_validate_llm_mapping_rejects_unknown_or_low_confidence_paths(self):
        requested_slot_ids = {"paragraph[0]", "paragraph[1]"}
        allowed_source_paths = {"risk_change.content"}
        llm_mapping = {
            "mappings": [
                {
                    "slot_id": "paragraph[0]",
                    "template_label": "x",
                    "source_path": "diagnosis",
                    "confidence": "high",
                    "reason": "unsafe",
                },
                {
                    "slot_id": "paragraph[1]",
                    "template_label": "y",
                    "source_path": "risk_change.content",
                    "confidence": "low",
                    "reason": "weak",
                },
            ]
        }

        validated = validate_llm_mapping(llm_mapping, requested_slot_ids, allowed_source_paths)

        self.assertEqual(validated["mappings"][0]["source_path"], "unmapped")
        self.assertEqual(validated["mappings"][0]["confidence"], "none")
        self.assertEqual(validated["mappings"][0]["fill_status"], "skipped")
        self.assertEqual(validated["mappings"][1]["source_path"], "risk_change.content")
        self.assertEqual(validated["mappings"][1]["fill_status"], "skipped")

    def test_merge_template_mappings_replaces_only_unresolved_slots(self):
        base_mapping = {
            "mappings": [
                {
                    "slot_id": "paragraph[0]",
                    "template_label": "鍜ㄨ鐩爣",
                    "source_path": "unmapped",
                    "confidence": "none",
                    "fill_status": "skipped",
                    "reason": "No deterministic source path match.",
                },
                {
                    "slot_id": "table[0].row[0].cell[1]",
                    "template_label": "椋庨櫓鍙樺寲",
                    "source_path": "risk_change.content",
                    "confidence": "high",
                    "fill_status": "ready",
                    "reason": "Rule match.",
                },
            ]
        }
        llm_mapping = {
            "mappings": [
                {
                    "slot_id": "paragraph[0]",
                    "template_label": "鍜ㄨ鐩爣",
                    "source_path": "next_session_focus",
                    "confidence": "medium",
                    "fill_status": "ready",
                    "reason": "LLM mapped to allowed source.",
                }
            ]
        }

        merged = merge_template_mappings(base_mapping, llm_mapping)

        self.assertEqual(merged["mappings"][0]["source_path"], "next_session_focus")
        self.assertEqual(merged["mappings"][1]["source_path"], "risk_change.content")

    def test_unresolved_mapping_items_returns_skipped_items(self):
        mapping = build_template_mapping(
            extract_template_slots_from_xml(self.unknown_placeholder_xml()),
            build_source_paths(self.sample_w3()),
        )

        unresolved = unresolved_mapping_items(mapping)

        self.assertEqual(len(unresolved), 1)
        self.assertEqual(unresolved[0]["source_path"], "unmapped")

    def test_run_deepseek_template_mapping_merges_fake_api_result(self):
        base_mapping = build_template_mapping(
            extract_template_slots_from_xml(self.unknown_placeholder_xml()),
            build_source_paths(self.sample_w3()),
        )
        source_paths = build_source_paths(self.sample_w3())
        calls = []

        def fake_post(url, headers, payload, timeout):
            calls.append({"url": url, "headers": headers, "payload": payload, "timeout": timeout})
            return {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "mappings": [
                                        {
                                            "slot_id": "paragraph[0]",
                                            "template_label": "鍜ㄨ鐩爣",
                                            "source_path": "next_session_focus",
                                            "confidence": "medium",
                                            "reason": "Allowed source path matches a future-oriented plan field.",
                                        }
                                    ]
                                },
                                ensure_ascii=False,
                            )
                        }
                    }
                ]
            }

        result = run_deepseek_template_mapping(
            base_mapping,
            source_paths,
            DeepSeekConfig(api_key="test-key", model="deepseek-v4-flash", base_url="https://example.test"),
            http_post_json=fake_post,
        )

        self.assertEqual(result["llm_status"], "success")
        self.assertEqual(len(calls), 1)
        self.assertEqual(result["mapping"]["mappings"][0]["source_path"], "next_session_focus")
        self.assertEqual(result["mapping"]["mappings"][0]["fill_status"], "ready")

    def test_run_deepseek_template_mapping_skips_api_when_no_unresolved_slots(self):
        base_mapping = build_template_mapping(
            extract_template_slots_from_xml(self.template_xml()),
            build_source_paths(self.sample_w3()),
        )
        calls = []

        def fake_post(url, headers, payload, timeout):
            calls.append(payload)
            return {}

        result = run_deepseek_template_mapping(
            base_mapping,
            build_source_paths(self.sample_w3()),
            DeepSeekConfig(api_key="test-key"),
            http_post_json=fake_post,
        )

        self.assertEqual(result["llm_status"], "skipped")
        self.assertEqual(calls, [])
        self.assertEqual(result["mapping"], base_mapping)

    def template_xml(self):
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<w:document xmlns:w="{WORD_NS}">'
            "<w:body>"
            "<w:tbl>"
            "<w:tr>"
            "<w:tc><w:p><w:r><w:t>风险变化</w:t></w:r></w:p></w:tc>"
            "<w:tc><w:p><w:r><w:t>____</w:t></w:r></w:p></w:tc>"
            "</w:tr>"
            "</w:tbl>"
            "<w:p><w:r><w:t>下次咨询重点：____</w:t></w:r></w:p>"
            "<w:sectPr/>"
            "</w:body>"
            "</w:document>"
        )

    def unknown_placeholder_xml(self):
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<w:document xmlns:w="{WORD_NS}">'
            "<w:body>"
            "<w:p><w:r><w:t>咨询目标：____</w:t></w:r></w:p>"
            "<w:sectPr/>"
            "</w:body>"
            "</w:document>"
        )

    def non_placeholder_table_xml(self):
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<w:document xmlns:w="{WORD_NS}">'
            "<w:body>"
            "<w:tbl>"
            "<w:tr>"
            "<w:tc><w:p><w:r><w:t>风险变化</w:t></w:r></w:p></w:tc>"
            "<w:tc><w:p><w:r><w:t>人工已有内容</w:t></w:r></w:p></w:tc>"
            "</w:tr>"
            "</w:tbl>"
            "<w:sectPr/>"
            "</w:body>"
            "</w:document>"
        )

    def read_document_xml(self, docx_path):
        with zipfile.ZipFile(docx_path) as package:
            return package.read("word/document.xml").decode("utf-8")

    def test_fill_docx_template_updates_table_cell_and_paragraph_placeholder(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            template_path = tmp_path / "template.docx"
            structured_path = tmp_path / "structured_output.json"
            output_path = tmp_path / "filled_template.docx"
            report_path = tmp_path / "template_fill_report.json"
            write_docx_package(template_path, self.template_xml())
            structured_path.write_text(json.dumps(self.sample_w3(), ensure_ascii=False), encoding="utf-8")

            report = fill_docx_template(template_path, structured_path, output_path, report_path)

            document_xml = self.read_document_xml(output_path)
            saved_report = json.loads(report_path.read_text(encoding="utf-8"))

        self.assertEqual(report["status"], "PASS")
        self.assertEqual(saved_report["status"], "PASS")
        self.assertIn("出现被动自杀意念，无具体计划。", document_xml)
        self.assertIn("下次咨询重点：继续评估安全情况", document_xml)
        self.assertEqual(len(saved_report["filled_fields"]), 2)

    def test_unmatched_paragraph_placeholder_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            template_path = tmp_path / "template.docx"
            structured_path = tmp_path / "structured_output.json"
            output_path = tmp_path / "filled_template.docx"
            report_path = tmp_path / "template_fill_report.json"
            write_docx_package(template_path, self.unknown_placeholder_xml())
            structured_path.write_text(json.dumps(self.sample_w3(), ensure_ascii=False), encoding="utf-8")

            report = fill_docx_template(template_path, structured_path, output_path, report_path)

        self.assertEqual(report["status"], "WARN")
        self.assertEqual(report["unfilled_fields"][0]["template_label"], "咨询目标")
        self.assertEqual(report["unfilled_fields"][0]["reason"], "No matching structured field")

    def test_non_placeholder_target_cell_is_not_overwritten_and_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            template_path = tmp_path / "template.docx"
            structured_path = tmp_path / "structured_output.json"
            output_path = tmp_path / "filled_template.docx"
            report_path = tmp_path / "template_fill_report.json"
            write_docx_package(template_path, self.non_placeholder_table_xml())
            structured_path.write_text(json.dumps(self.sample_w3(), ensure_ascii=False), encoding="utf-8")

            report = fill_docx_template(template_path, structured_path, output_path, report_path)
            document_xml = self.read_document_xml(output_path)

        self.assertEqual(report["status"], "WARN")
        self.assertIn("人工已有内容", document_xml)
        self.assertEqual(report["issues"][0]["level"], "WARN")
        self.assertEqual(report["issues"][0]["template_label"], "风险变化")

    def test_invalid_json_returns_fail_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            template_path = tmp_path / "template.docx"
            structured_path = tmp_path / "structured_output.json"
            output_path = tmp_path / "filled_template.docx"
            report_path = tmp_path / "template_fill_report.json"
            write_docx_package(template_path, self.template_xml())
            structured_path.write_text("{bad json", encoding="utf-8")

            report = fill_docx_template(template_path, structured_path, output_path, report_path)

        self.assertEqual(report["status"], "FAIL")
        self.assertEqual(report["issues"][0]["level"], "ERROR")

    def test_docx_without_document_xml_returns_fail_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            template_path = tmp_path / "template.docx"
            structured_path = tmp_path / "structured_output.json"
            output_path = tmp_path / "filled_template.docx"
            report_path = tmp_path / "template_fill_report.json"
            with zipfile.ZipFile(template_path, "w") as package:
                package.writestr("[Content_Types].xml", "")
            structured_path.write_text(json.dumps(self.sample_w3(), ensure_ascii=False), encoding="utf-8")

            report = fill_docx_template(template_path, structured_path, output_path, report_path)

        self.assertEqual(report["status"], "FAIL")
        self.assertIn("word/document.xml", report["issues"][0]["message"])

    def test_fill_docx_template_uses_mapping_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            template_path = tmp_path / "template.docx"
            structured_path = tmp_path / "structured_output.json"
            mapping_path = tmp_path / "template_mapping.json"
            output_path = tmp_path / "filled_template.docx"
            report_path = tmp_path / "template_fill_report.json"
            write_docx_package(template_path, self.template_xml())
            structured_path.write_text(json.dumps(self.sample_w3(), ensure_ascii=False), encoding="utf-8")
            mapping_path.write_text(
                json.dumps(
                    {
                        "mappings": [
                            {
                                "slot_id": "table[0].row[0].cell[1]",
                                "template_label": "风险变化",
                                "source_path": "risk_change.content",
                                "confidence": "high",
                                "fill_status": "ready",
                                "reason": "Reviewed mapping.",
                            }
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            report = fill_docx_template(template_path, structured_path, output_path, report_path, mapping_path=mapping_path)
            document_xml = self.read_document_xml(output_path)

        self.assertEqual(report["status"], "PASS")
        self.assertIn("出现被动自杀意念，无具体计划。", document_xml)
        self.assertEqual(report["filled_fields"][0]["source_path"], "risk_change.content")

    def test_fill_docx_template_does_not_fill_skipped_mapping(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            template_path = tmp_path / "template.docx"
            structured_path = tmp_path / "structured_output.json"
            mapping_path = tmp_path / "template_mapping.json"
            output_path = tmp_path / "filled_template.docx"
            report_path = tmp_path / "template_fill_report.json"
            write_docx_package(template_path, self.template_xml())
            structured_path.write_text(json.dumps(self.sample_w3(), ensure_ascii=False), encoding="utf-8")
            mapping_path.write_text(
                json.dumps(
                    {
                        "mappings": [
                            {
                                "slot_id": "paragraph[0]",
                                "template_label": "下次咨询重点",
                                "source_path": "next_session_focus",
                                "confidence": "low",
                                "fill_status": "skipped",
                                "reason": "Needs review.",
                            }
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            report = fill_docx_template(template_path, structured_path, output_path, report_path, mapping_path=mapping_path)
            document_xml = self.read_document_xml(output_path)

        self.assertEqual(report["status"], "WARN")
        self.assertNotIn("继续评估安全情况", document_xml)
        self.assertEqual(report["unfilled_fields"][0]["reason"], "Needs review.")

    def test_parse_args_accepts_template_structured_output_and_report(self):
        args = parse_args(
            [
                "--template",
                "template.docx",
                "--structured",
                "structured_output.json",
                "--output",
                "filled_template.docx",
                "--report",
                "template_fill_report.json",
                "--slots-output",
                "template_slots.json",
                "--source-paths-output",
                "source_paths.json",
                "--mapping-output",
                "template_mapping.json",
                "--mapping-input",
                "reviewed_mapping.json",
            ]
        )

        self.assertEqual(args.template, "template.docx")
        self.assertEqual(args.structured, "structured_output.json")
        self.assertEqual(args.output, "filled_template.docx")
        self.assertEqual(args.report, "template_fill_report.json")
        self.assertEqual(args.slots_output, "template_slots.json")
        self.assertEqual(args.source_paths_output, "source_paths.json")
        self.assertEqual(args.mapping_output, "template_mapping.json")
        self.assertEqual(args.mapping_input, "reviewed_mapping.json")

    def test_main_writes_output_and_default_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            template_path = tmp_path / "template.docx"
            structured_path = tmp_path / "structured_output.json"
            output_path = tmp_path / "filled_template.docx"
            report_path = tmp_path / "template_fill_report.json"
            write_docx_package(template_path, self.template_xml())
            structured_path.write_text(json.dumps(self.sample_w3(), ensure_ascii=False), encoding="utf-8")

            code = main(
                [
                    "--template",
                    str(template_path),
                    "--structured",
                    str(structured_path),
                    "--output",
                    str(output_path),
                ]
            )

            report = json.loads(report_path.read_text(encoding="utf-8"))
            output_exists = output_path.exists()

        self.assertEqual(code, 0)
        self.assertTrue(output_exists)
        self.assertEqual(report["status"], "PASS")

    def test_main_writes_mapping_artifact_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            template_path = tmp_path / "template.docx"
            structured_path = tmp_path / "structured_output.json"
            output_path = tmp_path / "filled_template.docx"
            slots_path = tmp_path / "template_slots.json"
            source_paths_path = tmp_path / "source_paths.json"
            mapping_path = tmp_path / "template_mapping.json"
            write_docx_package(template_path, self.template_xml())
            structured_path.write_text(json.dumps(self.sample_w3(), ensure_ascii=False), encoding="utf-8")

            code = main(
                [
                    "--template",
                    str(template_path),
                    "--structured",
                    str(structured_path),
                    "--output",
                    str(output_path),
                    "--slots-output",
                    str(slots_path),
                    "--source-paths-output",
                    str(source_paths_path),
                    "--mapping-output",
                    str(mapping_path),
                ]
            )

            slots = json.loads(slots_path.read_text(encoding="utf-8"))
            source_paths = json.loads(source_paths_path.read_text(encoding="utf-8"))
            mapping = json.loads(mapping_path.read_text(encoding="utf-8"))

        self.assertEqual(code, 0)
        self.assertEqual(slots["slots"][0]["slot_id"], "table[0].row[0].cell[1]")
        self.assertIn("risk_change.content", [item["source_path"] for item in source_paths["source_paths"]])
        self.assertEqual(mapping["mappings"][0]["source_path"], "risk_change.content")


if __name__ == "__main__":
    unittest.main()
