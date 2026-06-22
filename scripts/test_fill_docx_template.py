import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from fill_docx_template import (
    build_source_map,
    build_source_paths,
    build_template_mapping,
    build_template_draft_prompt,
    build_llm_mapping_prompt,
    extract_template_slots_from_xml,
    extract_llm_mapping_json,
    extract_template_draft_json,
    fill_docx_template,
    fill_docx_template_from_draft,
    fill_docx_template_from_raw,
    fill_docx_template_with_llm_mapping,
    find_source_match,
    merge_template_mappings,
    main,
    normalize_label,
    parse_args,
    run_deepseek_template_mapping,
    run_deepseek_template_draft,
    unresolved_mapping_items,
    validate_llm_mapping,
    validate_template_draft,
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

    def sample_w1_block(self):
        return {
            "workflow": "W1",
            "document_type": "intake_form",
            "title": "\u521d\u59cb\u8bbf\u8c08\u8868",
            "sections": [
                {
                    "heading": "\u6765\u8bbf\u8005\u4e3b\u8981\u56f0\u6270",
                    "fields": [
                        {
                            "label": "\u6765\u8bbf\u8005\u4e3b\u8981\u56f0\u6270",
                            "value": "\u8fd1\u671f\u60c5\u7eea\u4f4e\u843d\uff0c\u7761\u7720\u53d7\u5f71\u54cd\u3002",
                        }
                    ],
                }
            ],
            "boundary_notes": [],
        }

    def test_normalize_label_removes_punctuation_and_placeholders(self):
        self.assertEqual(normalize_label(" 风险变化：____ "), "风险变化")

    def test_build_source_map_exposes_w3_core_fields(self):
        source_map = build_source_map(self.sample_w3())

        match = find_source_match("风险变化", source_map)

        self.assertIsNotNone(match)
        self.assertEqual(match["source_path"], "risk_change.content")
        self.assertEqual(match["value"], "出现被动自杀意念，无具体计划。")

    def test_build_source_map_exposes_w3_risk_follow_up_fields(self):
        source_map = build_source_map(
            {
                "workflow": "W3",
                "document_type": "session_note",
                "title": "DAP counseling record",
                "record_format": "DAP",
                "sections": [
                    {"heading": "Data", "content": "Client reported lower anxiety but ongoing presentation worry."},
                    {"heading": "Assessment", "content": "Performance-threat thinking may still be active."},
                    {"heading": "Plan", "content": "Review coping rehearsal next time."},
                ],
                "risk_change": {
                    "content": "No new self-harm or suicide escalation was documented.",
                    "change_documentation": ["The note does not describe a new escalation in self-harm, suicide, violence, or substance risk."],
                    "follow_up_actions": ["Re-check ideation, access to means, and environmental safety if concern rises."],
                },
                "next_session_focus": ["Review the presentation outcome and coping follow-through."],
                "missing_information": ["No direct counselor observation was documented in the source note."],
                "boundary_notes": ["This is a counselor-facing record, not a diagnosis or final risk judgment."],
            }
        )

        paths = {entry["source_path"] for entry in source_map}

        self.assertIn("risk_change.change_documentation", paths)
        self.assertIn("risk_change.follow_up_actions", paths)

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

    def test_extract_template_slots_from_xml_finds_single_cell_table_blocks(self):
        slots = extract_template_slots_from_xml(self.block_table_xml())

        self.assertEqual(slots[0]["slot_id"], "table[0].row[0].cell[0]")
        self.assertEqual(slots[0]["label"], "\u6765\u8bbf\u8005\u4e3b\u8981\u56f0\u6270")
        self.assertEqual(slots[0]["slot_type"], "table_block_cell")

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
        self.assertIn("咨询目标", prompt)
        self.assertIn("next_session_focus", prompt)

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

    def test_extract_template_slots_can_include_prefilled_table_cells(self):
        slots = extract_template_slots_from_xml(self.prefilled_table_xml(), include_prefilled=True)

        self.assertEqual(slots[0]["slot_id"], "table[0].row[0].cell[1]")
        self.assertEqual(slots[0]["label"], "主要困扰")
        self.assertEqual(slots[0]["current_text"], "已有记录")

    def test_build_template_draft_prompt_includes_policy_style_and_raw_material(self):
        slots = extract_template_slots_from_xml(self.prefilled_table_xml(), include_prefilled=True)

        prompt = build_template_draft_prompt(
            slots,
            "来访者分手后情绪低落。",
            "warm_clinical",
            "",
            "merge",
        )

        self.assertIn("template_slots", prompt)
        self.assertIn("warm_clinical", prompt)
        self.assertIn("来访者分手后情绪低落", prompt)
        self.assertIn("append_to_existing", prompt)

    def test_extract_template_draft_json_accepts_fenced_json(self):
        answer = (
            "```json\n"
            "{\"drafts\":[{\"slot_id\":\"paragraph[0]\",\"template_label\":\"x\","
            "\"action\":\"fill_blank\",\"content\":\"内容\",\"confidence\":\"medium\","
            "\"evidence\":[\"材料\"],\"reason\":\"match\"}],\"global_warnings\":[]}"
            "\n```"
        )

        draft = extract_template_draft_json(answer)

        self.assertEqual(draft["drafts"][0]["content"], "内容")

    def test_validate_template_draft_rejects_unknown_slots_and_downgrades_replace(self):
        slots = extract_template_slots_from_xml(self.prefilled_table_xml(), include_prefilled=True)
        raw_draft = {
            "drafts": [
                {
                    "slot_id": "table[0].row[0].cell[1]",
                    "template_label": "主要困扰",
                    "action": "replace_existing",
                    "content": "整理后的主要困扰",
                    "confidence": "medium",
                    "evidence": ["分手后情绪低落"],
                    "reason": "raw material supports this field",
                },
                {
                    "slot_id": "bad-slot",
                    "template_label": "不存在",
                    "action": "fill_blank",
                    "content": "不应进入结果",
                    "confidence": "high",
                    "evidence": [],
                    "reason": "bad",
                },
            ],
            "global_warnings": ["需要进一步评估风险。"],
        }

        validated = validate_template_draft(raw_draft, slots, "merge")

        self.assertEqual(len(validated["drafts"]), 1)
        self.assertEqual(validated["drafts"][0]["action"], "append_to_existing")
        self.assertEqual(validated["global_warnings"], ["需要进一步评估风险。"])
        self.assertEqual(validated["issues"][0]["slot_id"], "bad-slot")

    def test_validate_template_draft_keeps_existing_when_policy_ask(self):
        slots = extract_template_slots_from_xml(self.prefilled_table_xml(), include_prefilled=True)
        raw_draft = {
            "drafts": [
                {
                    "slot_id": "table[0].row[0].cell[1]",
                    "template_label": "主要困扰",
                    "action": "revise_existing",
                    "content": "整理后的主要困扰",
                    "confidence": "medium",
                    "evidence": ["材料"],
                    "reason": "revise",
                }
            ]
        }

        validated = validate_template_draft(raw_draft, slots, "ask")

        self.assertEqual(validated["drafts"][0]["action"], "keep_existing")
        self.assertEqual(validated["drafts"][0]["content"], "")

    def test_validate_template_draft_preserves_protected_identity_fields(self):
        slots = extract_template_slots_from_xml(self.protected_identity_xml(), include_prefilled=True)
        raw_draft = {
            "drafts": [
                {
                    "slot_id": "paragraph[0]",
                    "template_label": "学号",
                    "action": "revise_existing",
                    "content": "学号：姓名：性别：女",
                    "confidence": "high",
                    "evidence": ["女"],
                    "reason": "partial identity field",
                }
            ]
        }

        validated = validate_template_draft(raw_draft, slots, "merge")

        self.assertEqual(validated["drafts"][0]["action"], "keep_existing")
        self.assertEqual(validated["drafts"][0]["content"], "")

    def test_fill_docx_template_from_draft_fills_blank_and_appends_existing(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            template_path = tmp_path / "template.docx"
            output_path = tmp_path / "filled_template.docx"
            report_path = tmp_path / "template_fill_report.json"
            draft_path = tmp_path / "template_draft.json"
            write_docx_package(template_path, self.blank_and_prefilled_xml())
            draft = {
                "drafts": [
                    {
                        "slot_id": "table[0].row[0].cell[1]",
                        "template_label": "主要困扰",
                        "action": "fill_blank",
                        "content": "来访者分手后情绪低落。",
                        "confidence": "medium",
                        "evidence": ["分手后情绪低落"],
                        "reason": "matched",
                    },
                    {
                        "slot_id": "table[0].row[1].cell[1]",
                        "template_label": "已有理解",
                        "action": "append_to_existing",
                        "content": "补充：社交支持使用较少。",
                        "confidence": "medium",
                        "evidence": ["很久没有告诉朋友"],
                        "reason": "append",
                    },
                ],
                "global_warnings": [],
                "issues": [],
            }

            report = fill_docx_template_from_draft(
                template_path,
                draft,
                output_path,
                report_path,
                draft_path=draft_path,
                existing_content_policy="merge",
            )
            document_xml = self.read_document_xml(output_path)

        self.assertEqual(report["status"], "PASS")
        self.assertIn("来访者分手后情绪低落", document_xml)
        self.assertIn("原有内容", document_xml)
        self.assertIn("补充：社交支持使用较少", document_xml)
        self.assertEqual(len(report["drafted_fields"]), 2)

    def test_fill_docx_template_from_draft_keeps_existing_under_blank_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            template_path = tmp_path / "template.docx"
            output_path = tmp_path / "filled_template.docx"
            report_path = tmp_path / "template_fill_report.json"
            write_docx_package(template_path, self.prefilled_table_xml())
            draft = {
                "drafts": [
                    {
                        "slot_id": "table[0].row[0].cell[1]",
                        "template_label": "主要困扰",
                        "action": "replace_existing",
                        "content": "新内容",
                        "confidence": "medium",
                        "evidence": ["材料"],
                        "reason": "replace",
                    }
                ],
                "global_warnings": [],
                "issues": [],
            }

            report = fill_docx_template_from_draft(
                template_path,
                validate_template_draft(draft, extract_template_slots_from_xml(self.prefilled_table_xml(), include_prefilled=True), "blank_only"),
                output_path,
                report_path,
                existing_content_policy="blank_only",
            )
            document_xml = self.read_document_xml(output_path)

        self.assertEqual(report["status"], "WARN")
        self.assertIn("已有记录", document_xml)
        self.assertNotIn("新内容", document_xml)
        self.assertEqual(len(report["kept_fields"]), 1)

    def test_run_deepseek_template_draft_uses_fake_api_and_validates(self):
        slots = extract_template_slots_from_xml(self.blank_and_prefilled_xml(), include_prefilled=True)

        def fake_post(url, headers, payload, timeout):
            return {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "drafts": [
                                        {
                                            "slot_id": "table[0].row[0].cell[1]",
                                            "template_label": "主要困扰",
                                            "action": "fill_blank",
                                            "content": "来访者分手后情绪低落。",
                                            "confidence": "medium",
                                            "evidence": ["分手后情绪低落"],
                                            "reason": "supported",
                                        }
                                    ],
                                    "global_warnings": ["需持续评估风险。"],
                                },
                                ensure_ascii=False,
                            )
                        }
                    }
                ]
            }

        draft = run_deepseek_template_draft(
            slots,
            "来访者分手后情绪低落。",
            "professional_concise",
            "",
            "merge",
            DeepSeekConfig(api_key="test-key", model="deepseek-v4-flash", base_url="https://example.test"),
            http_post_json=fake_post,
        )

        self.assertEqual(draft["drafts"][0]["content"], "来访者分手后情绪低落。")
        self.assertEqual(draft["global_warnings"], ["需持续评估风险。"])

    def test_fill_docx_template_from_raw_writes_draft_and_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            template_path = tmp_path / "template.docx"
            output_path = tmp_path / "filled_template.docx"
            report_path = tmp_path / "template_fill_report.json"
            draft_path = tmp_path / "template_draft.json"
            write_docx_package(template_path, self.blank_and_prefilled_xml())

            def fake_post(url, headers, payload, timeout):
                return {
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps(
                                    {
                                        "drafts": [
                                            {
                                                "slot_id": "table[0].row[0].cell[1]",
                                                "template_label": "主要困扰",
                                                "action": "fill_blank",
                                                "content": "来访者分手后情绪低落。",
                                                "confidence": "medium",
                                                "evidence": ["分手后情绪低落"],
                                                "reason": "supported",
                                            }
                                        ],
                                        "global_warnings": [],
                                    },
                                    ensure_ascii=False,
                                )
                            }
                        }
                    ]
                }

            report = fill_docx_template_from_raw(
                template_path,
                "来访者分手后情绪低落。",
                output_path,
                report_path,
                draft_path,
                config=DeepSeekConfig(api_key="test-key", model="deepseek-v4-flash", base_url="https://example.test"),
                http_post_json=fake_post,
            )
            draft = json.loads(draft_path.read_text(encoding="utf-8"))
            document_xml = self.read_document_xml(output_path)

        self.assertEqual(report["status"], "PASS")
        self.assertEqual(draft["drafts"][0]["action"], "fill_blank")
        self.assertIn("来访者分手后情绪低落", document_xml)

    def prefilled_table_xml(self):
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<w:document xmlns:w="{WORD_NS}">'
            "<w:body>"
            "<w:tbl>"
            "<w:tr>"
            "<w:tc><w:p><w:r><w:t>主要困扰</w:t></w:r></w:p></w:tc>"
            "<w:tc><w:p><w:r><w:t>已有记录</w:t></w:r></w:p></w:tc>"
            "</w:tr>"
            "</w:tbl>"
            "<w:sectPr/>"
            "</w:body>"
            "</w:document>"
        )

    def blank_and_prefilled_xml(self):
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<w:document xmlns:w="{WORD_NS}">'
            "<w:body>"
            "<w:tbl>"
            "<w:tr>"
            "<w:tc><w:p><w:r><w:t>主要困扰</w:t></w:r></w:p></w:tc>"
            "<w:tc><w:p><w:r><w:t>____</w:t></w:r></w:p></w:tc>"
            "</w:tr>"
            "<w:tr>"
            "<w:tc><w:p><w:r><w:t>已有理解</w:t></w:r></w:p></w:tc>"
            "<w:tc><w:p><w:r><w:t>原有内容</w:t></w:r></w:p></w:tc>"
            "</w:tr>"
            "</w:tbl>"
            "<w:sectPr/>"
            "</w:body>"
            "</w:document>"
        )

    def protected_identity_xml(self):
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<w:document xmlns:w="{WORD_NS}">'
            "<w:body>"
            "<w:p><w:r><w:t>学号：姓名：性别： 咨询时间：</w:t></w:r></w:p>"
            "<w:sectPr/>"
            "</w:body>"
            "</w:document>"
        )

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

    def block_table_xml(self):
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<w:document xmlns:w="{WORD_NS}">'
            "<w:body>"
            "<w:tbl>"
            "<w:tr>"
            "<w:tc><w:p><w:r><w:t>\u6765\u8bbf\u8005\u4e3b\u8981\u56f0\u6270</w:t></w:r></w:p></w:tc>"
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

    def test_fill_docx_template_fills_single_cell_table_block(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            template_path = tmp_path / "template.docx"
            structured_path = tmp_path / "structured_output.json"
            mapping_path = tmp_path / "template_mapping.json"
            output_path = tmp_path / "filled_template.docx"
            report_path = tmp_path / "template_fill_report.json"
            write_docx_package(template_path, self.block_table_xml())
            structured_path.write_text(json.dumps(self.sample_w1_block(), ensure_ascii=False), encoding="utf-8")
            mapping_path.write_text(
                json.dumps(
                    {
                        "mappings": [
                            {
                                "slot_id": "table[0].row[0].cell[0]",
                                "template_label": "\u6765\u8bbf\u8005\u4e3b\u8981\u56f0\u6270",
                                "source_path": "sections[0].fields[0].value",
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
        self.assertIn("\u6765\u8bbf\u8005\u4e3b\u8981\u56f0\u6270", document_xml)
        self.assertIn("\u8fd1\u671f\u60c5\u7eea\u4f4e\u843d", document_xml)

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

    def test_fill_docx_template_with_llm_mapping_fills_unresolved_slot_and_writes_mapping(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            template_path = tmp_path / "template.docx"
            structured_path = tmp_path / "structured_output.json"
            output_path = tmp_path / "filled_template.docx"
            report_path = tmp_path / "template_fill_report.json"
            mapping_path = tmp_path / "template_mapping.json"
            write_docx_package(template_path, self.unknown_placeholder_xml())
            structured_path.write_text(json.dumps(self.sample_w3(), ensure_ascii=False), encoding="utf-8")

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
                                                "reason": "This slot asks for a forward-looking counseling target.",
                                            }
                                        ]
                                    },
                                    ensure_ascii=False,
                                )
                            }
                        }
                    ]
                }

            report = fill_docx_template_with_llm_mapping(
                template_path,
                structured_path,
                output_path,
                report_path,
                mapping_output_path=mapping_path,
                config=DeepSeekConfig(api_key="test-key", model="deepseek-v4-flash", base_url="https://example.test"),
                http_post_json=fake_post,
            )
            document_xml = self.read_document_xml(output_path)
            saved_mapping = json.loads(mapping_path.read_text(encoding="utf-8"))

        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["llm_status"], "success")
        self.assertEqual(saved_mapping["mappings"][0]["source_path"], "next_session_focus")
        self.assertIn("咨询目标", document_xml)
        self.assertIn("继续评估安全情况", document_xml)

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
                "--llm-map",
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
        self.assertTrue(args.llm_map)

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
