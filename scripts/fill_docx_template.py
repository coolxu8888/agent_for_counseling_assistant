import argparse
import json
import re
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from run_model_eval import (
    build_chat_payload,
    deepseek_chat_completions_url,
    extract_answer_text,
    post_json,
)


PLACEHOLDER_CHARS = "_＿—-"
PUNCTUATION_PATTERN = re.compile(r"[\s：:（）()\[\]【】{}<>《》、，,。.;；/\\|]+")
WORD_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": WORD_NS}
P_TAG = f"{{{WORD_NS}}}p"
TBL_TAG = f"{{{WORD_NS}}}tbl"
TR_TAG = f"{{{WORD_NS}}}tr"
TC_TAG = f"{{{WORD_NS}}}tc"
TEXT_TAG = f"{{{WORD_NS}}}t"
ET.register_namespace("w", WORD_NS)


def normalize_label(label):
    text = "" if label is None else str(label)
    text = PUNCTUATION_PATTERN.sub("", text)
    for char in PLACEHOLDER_CHARS:
        text = text.replace(char, "")
    return text.strip()


def render_value(value):
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (list, tuple)):
        return "\n".join(render_value(item) for item in value if render_value(item))
    if isinstance(value, dict):
        return "\n".join(
            f"{key}：{render_value(item)}" for key, item in value.items() if render_value(item)
        )
    return str(value)


def _entry(source_path, value, aliases):
    clean_value = render_value(value)
    return {
        "source_path": source_path,
        "value": clean_value,
        "aliases": [alias for alias in aliases if alias],
        "normalized_aliases": [normalize_label(alias) for alias in aliases if alias],
    }


def _add_entry(entries, source_path, value, aliases):
    rendered = render_value(value)
    if rendered:
        entries.append(_entry(source_path, rendered, aliases))


def _add_section_entries(entries, sections):
    for index, section in enumerate(sections or []):
        heading = section.get("heading") or section.get("title") or ""
        content = section.get("content")
        if content:
            _add_entry(entries, f"sections[{index}].content", content, [heading])
        fields = section.get("fields") or []
        if fields:
            field_lines = []
            for field_index, field in enumerate(fields):
                label = field.get("label") or field.get("id") or ""
                value = field.get("value") or field.get("notes") or "待填写"
                field_lines.append(f"{label}：{value}")
                _add_entry(
                    entries,
                    f"sections[{index}].fields[{field_index}].value",
                    value,
                    [label],
                )
            _add_entry(entries, f"sections[{index}].fields", field_lines, [heading])


def build_source_map(data):
    entries = []
    if not isinstance(data, dict):
        return entries

    _add_entry(entries, "title", data.get("title"), ["标题", "文档标题", data.get("title")])
    _add_section_entries(entries, data.get("sections"))

    document_type = data.get("document_type")
    if document_type == "session_note":
        risk_change = data.get("risk_change") or {}
        _add_entry(
            entries,
            "risk_change.content",
            risk_change.get("content"),
            ["风险变化", "风险评估", "自杀自伤风险", "危机风险"],
        )
        _add_entry(entries, "next_session_focus", data.get("next_session_focus"), ["下次咨询重点", "后续计划"])
        _add_entry(entries, "missing_information", data.get("missing_information"), ["待补充信息", "信息缺口"])
    elif document_type == "case_summary":
        bps = data.get("bio_psycho_social") or {}
        _add_entry(entries, "known_facts", data.get("known_facts"), ["已知事实", "个案背景", "基本情况"])
        _add_entry(entries, "bio_psycho_social.biological", bps.get("biological"), ["生物维度", "身体状态"])
        _add_entry(entries, "bio_psycho_social.psychological", bps.get("psychological"), ["心理维度", "心理状态"])
        _add_entry(entries, "bio_psycho_social.social", bps.get("social"), ["社会维度", "社会支持"])
        _add_entry(entries, "risk_signals", data.get("risk_signals"), ["风险信号", "风险变化", "危机风险"])
        _add_entry(entries, "information_gaps", data.get("information_gaps"), ["信息缺口", "待补充信息"])
        _add_entry(entries, "suggested_questions", data.get("suggested_questions"), ["建议进一步询问", "追问问题"])
    elif document_type == "intake_form":
        for alias in ["基本信息", "来访原因", "当前困扰", "风险评估", "知情同意"]:
            matching_sections = [
                section
                for section in data.get("sections", [])
                if normalize_label(alias) in normalize_label(section.get("heading", ""))
            ]
            if matching_sections:
                _add_entry(entries, f"sections.{normalize_label(alias)}", matching_sections, [alias])

    _add_entry(entries, "boundary_notes", data.get("boundary_notes"), ["边界说明", "伦理边界", "注意事项"])
    return entries


def find_source_match(template_label, source_map):
    normalized = normalize_label(template_label)
    if not normalized:
        return None

    medium_match = None
    for entry in source_map:
        for alias in entry["normalized_aliases"]:
            if not alias:
                continue
            if normalized == alias:
                return {
                    "source_path": entry["source_path"],
                    "value": entry["value"],
                    "confidence": "high",
                }
            if normalized in alias or alias in normalized:
                medium_match = {
                    "source_path": entry["source_path"],
                    "value": entry["value"],
                    "confidence": "medium",
                }
    return medium_match


def build_source_paths(data):
    source_paths = []
    for entry in build_source_map(data):
        source_paths.append(
            {
                "source_path": entry["source_path"],
                "value": entry["value"],
                "aliases": entry["aliases"],
            }
        )
    return source_paths


def _source_path_match(template_label, source_paths):
    source_map = []
    for item in source_paths:
        source_map.append(
            {
                "source_path": item["source_path"],
                "value": item.get("value", ""),
                "aliases": item.get("aliases", []),
                "normalized_aliases": [normalize_label(alias) for alias in item.get("aliases", [])],
            }
        )
    return find_source_match(template_label, source_map)


def build_template_mapping(slots, source_paths):
    mappings = []
    for slot in slots:
        match = _source_path_match(slot.get("label", ""), source_paths)
        if match:
            mappings.append(
                {
                    "slot_id": slot["slot_id"],
                    "template_label": slot.get("label", ""),
                    "source_path": match["source_path"],
                    "confidence": match["confidence"],
                    "fill_status": "ready",
                    "reason": "Rule match.",
                }
            )
        else:
            mappings.append(
                {
                    "slot_id": slot["slot_id"],
                    "template_label": slot.get("label", ""),
                    "source_path": "unmapped",
                    "confidence": "none",
                    "fill_status": "skipped",
                    "reason": "No deterministic source path match.",
                }
            )
    return {"mappings": mappings}


def unresolved_mapping_items(mapping):
    return [
        item
        for item in mapping.get("mappings", [])
        if item.get("fill_status") != "ready" or item.get("source_path") == "unmapped"
    ]


def build_llm_mapping_prompt(slots, source_paths):
    prompt_package = {
        "task": "Map DOCX template slots to allowed structured source paths. Return JSON only.",
        "rules": [
            "Do not create new text for the Word document.",
            "Choose source_path only from allowed source paths or use unmapped.",
            "Use confidence high, medium, low, or none.",
            "Use unmapped when the slot asks for diagnosis, unsupported risk level, missing facts, or unsafe/private information not present in sources.",
            "Low and none will not be filled automatically.",
        ],
        "response_schema": {
            "mappings": [
                {
                    "slot_id": "string",
                    "template_label": "string",
                    "source_path": "allowed source_path or unmapped",
                    "confidence": "high|medium|low|none",
                    "reason": "brief reason",
                }
            ]
        },
        "template_slots": slots,
        "allowed_source_paths": source_paths,
    }
    return (
        "You are a constrained template mapping assistant. Return JSON only.\n"
        "Do not infer diagnoses, final risk levels, or missing personal information.\n\n"
        + json.dumps(prompt_package, ensure_ascii=False, indent=2, sort_keys=True)
    )


def extract_llm_mapping_json(answer_text):
    text = (answer_text or "").strip()
    blocks = re.findall(r"```json\s*(.*?)\s*```", text, flags=re.IGNORECASE | re.DOTALL)
    candidate = blocks[-1].strip() if blocks else text
    return json.loads(candidate)


def _validated_skipped_mapping(item, reason):
    return {
        "slot_id": item.get("slot_id", ""),
        "template_label": item.get("template_label", ""),
        "source_path": "unmapped",
        "confidence": "none",
        "fill_status": "skipped",
        "reason": reason,
    }


def validate_llm_mapping(mapping, requested_slot_ids, allowed_source_paths):
    valid_confidences = {"high", "medium", "low", "none"}
    validated = []
    for raw_item in mapping.get("mappings", []):
        slot_id = raw_item.get("slot_id")
        if slot_id not in requested_slot_ids:
            continue
        confidence = raw_item.get("confidence", "none")
        if confidence not in valid_confidences:
            confidence = "none"
        source_path = raw_item.get("source_path", "unmapped")
        if source_path != "unmapped" and source_path not in allowed_source_paths:
            validated.append(_validated_skipped_mapping(raw_item, "LLM returned an unknown source_path."))
            continue
        fill_status = "ready" if source_path != "unmapped" and confidence in {"high", "medium"} else "skipped"
        validated.append(
            {
                "slot_id": slot_id,
                "template_label": raw_item.get("template_label", ""),
                "source_path": source_path,
                "confidence": confidence,
                "fill_status": fill_status,
                "reason": raw_item.get("reason", "LLM mapping."),
            }
        )
    return {"mappings": validated}


def merge_template_mappings(base_mapping, llm_mapping):
    llm_by_slot = {item.get("slot_id"): item for item in llm_mapping.get("mappings", [])}
    merged = []
    for item in base_mapping.get("mappings", []):
        slot_id = item.get("slot_id")
        replacement = llm_by_slot.get(slot_id)
        if replacement and (item.get("fill_status") != "ready" or item.get("source_path") == "unmapped"):
            merged.append(replacement)
        else:
            merged.append(item)
    return {"mappings": merged}


def run_deepseek_template_mapping(base_mapping, source_paths, config, http_post_json=post_json):
    unresolved = unresolved_mapping_items(base_mapping)
    if not unresolved:
        return {
            "mapping": base_mapping,
            "llm_status": "skipped",
            "llm_issues": [],
        }

    try:
        prompt = build_llm_mapping_prompt(unresolved, source_paths)
        payload = build_chat_payload(config.model, prompt)
        response_json = http_post_json(
            deepseek_chat_completions_url(config.base_url),
            {"Authorization": f"Bearer {config.api_key}"},
            payload,
            config.timeout_seconds,
        )
        answer_text = extract_answer_text(response_json)
        raw_mapping = extract_llm_mapping_json(answer_text)
        validated_mapping = validate_llm_mapping(
            raw_mapping,
            {item.get("slot_id") for item in unresolved},
            {item.get("source_path") for item in source_paths},
        )
        return {
            "mapping": merge_template_mappings(base_mapping, validated_mapping),
            "llm_status": "success",
            "llm_issues": [],
        }
    except Exception as exc:
        return {
            "mapping": base_mapping,
            "llm_status": "error",
            "llm_issues": [{"level": "ERROR", "message": str(exc)[:500]}],
        }


def extract_template_slots_from_xml(document_xml):
    root = ET.fromstring(document_xml)
    slots = []

    for table_index, table in enumerate(root.iter(TBL_TAG)):
        for row_index, row in enumerate(table.iter(TR_TAG)):
            cells = list(row.iter(TC_TAG))
            for cell_index, cell in enumerate(cells[:-1]):
                label = element_text(cell).strip()
                target = cells[cell_index + 1]
                target_text = element_text(target)
                if label and is_placeholder_text(target_text):
                    location = f"table[{table_index}].row[{row_index}].cell[{cell_index + 1}]"
                    slots.append(
                        {
                            "slot_id": location,
                            "label": label,
                            "location": location,
                            "slot_type": "table_adjacent_cell",
                            "current_text": target_text,
                        }
                    )

    paragraph_slot_index = 0
    for paragraph in root.iter(P_TAG):
        text = element_text(paragraph)
        parsed = _paragraph_label_and_placeholder(text)
        if not parsed:
            continue
        label, _separator = parsed
        location = f"paragraph[{paragraph_slot_index}]"
        slots.append(
            {
                "slot_id": location,
                "label": label,
                "location": location,
                "slot_type": "paragraph_placeholder",
                "current_text": text,
            }
        )
        paragraph_slot_index += 1

    return slots


def extract_template_slots(template_path):
    with zipfile.ZipFile(template_path, "r") as package:
        if "word/document.xml" not in package.namelist():
            raise ValueError("DOCX template is missing word/document.xml.")
        return extract_template_slots_from_xml(package.read("word/document.xml"))


def _slot_targets(root):
    targets = {}
    for table_index, table in enumerate(root.iter(TBL_TAG)):
        for row_index, row in enumerate(table.iter(TR_TAG)):
            cells = list(row.iter(TC_TAG))
            for cell_index, cell in enumerate(cells[:-1]):
                label = element_text(cell).strip()
                target = cells[cell_index + 1]
                target_text = element_text(target)
                if label and is_placeholder_text(target_text):
                    location = f"table[{table_index}].row[{row_index}].cell[{cell_index + 1}]"
                    targets[location] = {
                        "element": target,
                        "label": label,
                        "location": location,
                        "slot_type": "table_adjacent_cell",
                        "current_text": target_text,
                    }

    paragraph_slot_index = 0
    for paragraph in root.iter(P_TAG):
        text = element_text(paragraph)
        parsed = _paragraph_label_and_placeholder(text)
        if not parsed:
            continue
        label, separator = parsed
        location = f"paragraph[{paragraph_slot_index}]"
        targets[location] = {
            "element": paragraph,
            "label": label,
            "separator": separator,
            "location": location,
            "slot_type": "paragraph_placeholder",
            "current_text": text,
        }
        paragraph_slot_index += 1
    return targets


def element_text(element):
    return "".join(text_node.text or "" for text_node in element.iter(TEXT_TAG))


def set_element_text(element, text):
    text_nodes = list(element.iter(TEXT_TAG))
    if text_nodes:
        text_nodes[0].text = text
        for extra_node in text_nodes[1:]:
            extra_node.text = ""
        return

    paragraph = element.find(f".//{P_TAG}")
    if paragraph is None:
        paragraph = ET.SubElement(element, f"{{{WORD_NS}}}p")
    run = ET.SubElement(paragraph, f"{{{WORD_NS}}}r")
    text_node = ET.SubElement(run, f"{{{WORD_NS}}}t")
    text_node.text = text


def is_placeholder_text(value):
    stripped = (value or "").strip()
    if not stripped:
        return True
    if stripped in {"待填写", "待补充", "未提供", "空", "N/A"}:
        return True
    return all(char in PLACEHOLDER_CHARS or char.isspace() for char in stripped)


def _base_report(template_path, structured_path, output_path):
    return {
        "status": "WARN",
        "template_file": str(template_path),
        "structured_file": str(structured_path),
        "output_file": str(output_path),
        "filled_fields": [],
        "unfilled_fields": [],
        "issues": [],
    }


def _finalize_report(report):
    if any(issue.get("level") == "ERROR" for issue in report["issues"]):
        report["status"] = "FAIL"
    elif report["filled_fields"] and not report["unfilled_fields"] and not report["issues"]:
        report["status"] = "PASS"
    elif report["filled_fields"]:
        report["status"] = "WARN"
    else:
        report["status"] = "WARN"
    return report


def write_report(path, report):
    report_path = Path(path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_json_file(path, data):
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _record_filled(report, template_label, match, location):
    report["filled_fields"].append(
        {
            "template_label": template_label,
            "source_path": match["source_path"],
            "confidence": match["confidence"],
            "location": location,
        }
    )


def fill_tables(root, source_map, report):
    for table_index, table in enumerate(root.iter(TBL_TAG)):
        for row_index, row in enumerate(table.iter(TR_TAG)):
            cells = list(row.iter(TC_TAG))
            for cell_index, cell in enumerate(cells[:-1]):
                label = element_text(cell).strip()
                match = find_source_match(label, source_map)
                if not match:
                    continue
                target = cells[cell_index + 1]
                target_text = element_text(target)
                location = f"table[{table_index}].row[{row_index}].cell[{cell_index + 1}]"
                if not is_placeholder_text(target_text):
                    report["issues"].append(
                        {
                            "level": "WARN",
                            "message": "Target cell already contains non-placeholder text.",
                            "template_label": label,
                            "location": location,
                        }
                    )
                    continue
                set_element_text(target, match["value"])
                _record_filled(report, label, match, location)


def _paragraph_label_and_placeholder(text):
    match = re.match(r"^\s*(?P<label>[^：:\n]{1,40})(?P<sep>[：:])(?P<value>.*)$", text or "")
    if not match:
        return None
    value = match.group("value")
    if not is_placeholder_text(value):
        return None
    return match.group("label").strip(), match.group("sep")


def fill_paragraphs(root, source_map, report):
    for paragraph_index, paragraph in enumerate(root.iter(P_TAG)):
        text = element_text(paragraph)
        parsed = _paragraph_label_and_placeholder(text)
        if not parsed:
            continue
        label, separator = parsed
        match = find_source_match(label, source_map)
        location = f"paragraph[{paragraph_index}]"
        if not match:
            report["unfilled_fields"].append(
                {
                    "template_label": label,
                    "reason": "No matching structured field",
                    "location": location,
                }
            )
            continue
        set_element_text(paragraph, f"{label}{separator}{match['value']}")
        _record_filled(report, label, match, location)


def _source_values_by_path(data):
    return {item["source_path"]: item["value"] for item in build_source_paths(data)}


def fill_slots_by_mapping(root, source_values, mapping, report):
    targets = _slot_targets(root)
    for item in mapping.get("mappings", []):
        slot_id = item.get("slot_id")
        template_label = item.get("template_label", "")
        if item.get("fill_status") != "ready" or item.get("source_path") == "unmapped":
            report["unfilled_fields"].append(
                {
                    "template_label": template_label,
                    "reason": item.get("reason", "Mapping is not ready to fill."),
                    "location": slot_id,
                }
            )
            continue

        target = targets.get(slot_id)
        if not target:
            report["unfilled_fields"].append(
                {
                    "template_label": template_label,
                    "reason": "Mapped slot was not found in the template.",
                    "location": slot_id,
                }
            )
            continue

        source_path = item.get("source_path")
        value = source_values.get(source_path)
        if not value:
            report["unfilled_fields"].append(
                {
                    "template_label": template_label,
                    "reason": "Mapped source path was not found in structured output.",
                    "location": slot_id,
                }
            )
            continue

        current_text = element_text(target["element"])
        if not is_placeholder_text(current_text) and target["slot_type"] != "paragraph_placeholder":
            report["issues"].append(
                {
                    "level": "WARN",
                    "message": "Target slot already contains non-placeholder text.",
                    "template_label": template_label,
                    "location": slot_id,
                }
            )
            continue

        if target["slot_type"] == "paragraph_placeholder":
            text = f"{target['label']}{target.get('separator', '：')}{value}"
        else:
            text = value
        set_element_text(target["element"], text)
        _record_filled(
            report,
            template_label or target["label"],
            {
                "source_path": source_path,
                "value": value,
                "confidence": item.get("confidence", "medium"),
            },
            slot_id,
        )


def fill_document_xml(document_xml, data, report, mapping=None):
    root = ET.fromstring(document_xml)
    if mapping is not None:
        fill_slots_by_mapping(root, _source_values_by_path(data), mapping, report)
    else:
        source_map = build_source_map(data)
        fill_tables(root, source_map, report)
        fill_paragraphs(root, source_map, report)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def report_failure(message, template_path=None, structured_path=None, output_path=None):
    report = _base_report(template_path or "", structured_path or "", output_path or "")
    report["status"] = "FAIL"
    report["issues"].append({"level": "ERROR", "message": message})
    return report


def fill_docx_template(template_path, structured_path, output_path, report_path, mapping_path=None):
    template = Path(template_path)
    structured = Path(structured_path)
    output = Path(output_path)
    report = _base_report(template, structured, output)

    try:
        data = json.loads(structured.read_text(encoding="utf-8"))
        mapping = json.loads(Path(mapping_path).read_text(encoding="utf-8")) if mapping_path else None
        with zipfile.ZipFile(template, "r") as source_package:
            if "word/document.xml" not in source_package.namelist():
                report = report_failure("DOCX template is missing word/document.xml.", template, structured, output)
            else:
                document_xml = source_package.read("word/document.xml")
                filled_xml = fill_document_xml(document_xml, data, report, mapping=mapping)
                output.parent.mkdir(parents=True, exist_ok=True)
                with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as output_package:
                    for item in source_package.infolist():
                        content = filled_xml if item.filename == "word/document.xml" else source_package.read(item.filename)
                        output_package.writestr(item, content)
                _finalize_report(report)
    except Exception as exc:
        report = report_failure(str(exc), template, structured, output)

    write_report(report_path, report)
    return report


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Fill a counselor DOCX template from structured output JSON.")
    parser.add_argument("--template", required=True, help="Path to the input .docx template.")
    parser.add_argument("--structured", required=True, help="Path to structured_output.json.")
    parser.add_argument("--output", required=True, help="Path to the filled .docx output.")
    parser.add_argument(
        "--report",
        default=None,
        help="Path to template_fill_report.json. Defaults to output directory/template_fill_report.json.",
    )
    parser.add_argument("--slots-output", default=None, help="Optional path to write template_slots.json.")
    parser.add_argument("--source-paths-output", default=None, help="Optional path to write source_paths.json.")
    parser.add_argument("--mapping-output", default=None, help="Optional path to write deterministic template_mapping.json.")
    parser.add_argument("--mapping-input", default=None, help="Optional reviewed template_mapping.json to use for filling.")
    return parser.parse_args(argv)


def write_mapping_artifacts(args):
    data = json.loads(Path(args.structured).read_text(encoding="utf-8"))
    slots = extract_template_slots(args.template)
    source_paths = build_source_paths(data)

    if args.slots_output:
        write_json_file(
            args.slots_output,
            {
                "template_file": str(args.template),
                "slots": slots,
            },
        )
    if args.source_paths_output:
        write_json_file(
            args.source_paths_output,
            {
                "structured_file": str(args.structured),
                "source_paths": source_paths,
            },
        )

    mapping_path = args.mapping_input
    if args.mapping_input:
        mapping = json.loads(Path(args.mapping_input).read_text(encoding="utf-8"))
    else:
        mapping = build_template_mapping(slots, source_paths)

    if args.mapping_output:
        write_json_file(args.mapping_output, mapping)
        mapping_path = args.mapping_output

    return mapping_path


def main(argv=None):
    args = parse_args(argv)
    output_path = Path(args.output)
    report_path = Path(args.report) if args.report else output_path.with_name("template_fill_report.json")
    try:
        mapping_path = write_mapping_artifacts(args)
    except Exception as exc:
        report = report_failure(str(exc), args.template, args.structured, output_path)
        write_report(report_path, report)
        print(f"DOCX template fill failed: {exc}", file=sys.stderr)
        return 1

    report = fill_docx_template(args.template, args.structured, output_path, report_path, mapping_path=mapping_path)
    if report["status"] == "FAIL":
        message = report["issues"][0]["message"] if report["issues"] else "Unknown error"
        print(f"DOCX template fill failed: {message}", file=sys.stderr)
        return 1
    print(f"DOCX template written: {output_path}")
    print(f"Template fill report written: {report_path}")
    if report["status"] == "WARN":
        print("Template fill completed with warnings. Review the report before use.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
