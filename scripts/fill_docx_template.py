import argparse
import json
import re
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


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


def fill_document_xml(document_xml, data, report):
    root = ET.fromstring(document_xml)
    source_map = build_source_map(data)
    fill_tables(root, source_map, report)
    fill_paragraphs(root, source_map, report)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def report_failure(message, template_path=None, structured_path=None, output_path=None):
    report = _base_report(template_path or "", structured_path or "", output_path or "")
    report["status"] = "FAIL"
    report["issues"].append({"level": "ERROR", "message": message})
    return report


def fill_docx_template(template_path, structured_path, output_path, report_path):
    template = Path(template_path)
    structured = Path(structured_path)
    output = Path(output_path)
    report = _base_report(template, structured, output)

    try:
        data = json.loads(structured.read_text(encoding="utf-8"))
        with zipfile.ZipFile(template, "r") as source_package:
            if "word/document.xml" not in source_package.namelist():
                report = report_failure("DOCX template is missing word/document.xml.", template, structured, output)
            else:
                document_xml = source_package.read("word/document.xml")
                filled_xml = fill_document_xml(document_xml, data, report)
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
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    output_path = Path(args.output)
    report_path = Path(args.report) if args.report else output_path.with_name("template_fill_report.json")
    report = fill_docx_template(args.template, args.structured, output_path, report_path)
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
