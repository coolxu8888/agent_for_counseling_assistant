import argparse
import json
import sys
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape


WORD_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def docx_success(output_path):
    return {"status": "PASS", "output_file": str(output_path), "issues": []}


def docx_failure(message):
    return {
        "status": "FAIL",
        "issues": [{"level": "ERROR", "message": message}],
    }


def _text(value):
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        return "；".join(_text(item) for item in value)
    if isinstance(value, dict):
        return "；".join(f"{key}: {_text(val)}" for key, val in value.items())
    return str(value)


def paragraph(text="", style=None):
    style_xml = ""
    if style:
        style_xml = f'<w:pPr><w:pStyle w:val="{escape(style)}"/></w:pPr>'
    return (
        "<w:p>"
        f"{style_xml}"
        "<w:r>"
        f"<w:t xml:space=\"preserve\">{escape(_text(text))}</w:t>"
        "</w:r>"
        "</w:p>"
    )


def table(rows):
    row_xml = []
    for row in rows:
        cells = []
        for cell in row:
            cells.append(f"<w:tc>{paragraph(cell)}</w:tc>")
        row_xml.append("<w:tr>" + "".join(cells) + "</w:tr>")
    return "<w:tbl>" + "".join(row_xml) + "</w:tbl>"


def truth_label(value):
    return "是" if value is True else "否"


def append_list(parts, title, items, empty_text="未提供"):
    parts.append(paragraph(title, "Heading2"))
    if items:
        for item in items:
            parts.append(paragraph("• " + _text(item)))
    else:
        parts.append(paragraph(empty_text))


def render_intake_form(data):
    parts = [paragraph(data.get("title") or "初访信息收集表", "Heading1")]
    for section in data.get("sections", []):
        parts.append(paragraph(section.get("heading", "未命名栏目"), "Heading2"))
        fields = section.get("fields", [])
        if fields:
            rows = [["字段", "内容", "必填", "敏感", "风险信号", "备注"]]
            for field in fields:
                rows.append(
                    [
                        field.get("label", field.get("id", "")),
                        field.get("value", "") or "待填写",
                        truth_label(field.get("required")),
                        truth_label(field.get("sensitive")),
                        truth_label(field.get("risk_signal")),
                        field.get("notes", ""),
                    ]
                )
            parts.append(table(rows))
        elif section.get("content"):
            parts.append(paragraph(section.get("content")))
    append_list(parts, "边界说明", data.get("boundary_notes", []))
    return parts


def render_case_summary(data):
    parts = [paragraph(data.get("title") or "个案信息整理", "Heading1")]
    append_list(parts, "已知事实", data.get("known_facts", []))
    bps = data.get("bio_psycho_social", {})
    parts.append(paragraph("生物-心理-社会信息", "Heading2"))
    for heading, key in [
        ("生物维度", "biological"),
        ("心理维度", "psychological"),
        ("社会维度", "social"),
    ]:
        append_list(parts, heading, bps.get(key, []) if isinstance(bps, dict) else [])
    risk_signals = data.get("risk_signals", [])
    append_list(
        parts,
        "风险信号",
        risk_signals,
        "材料中未见明确风险信号，建议咨询师按需进一步评估。",
    )
    append_list(parts, "信息缺口", data.get("information_gaps", []))
    parts.append(paragraph("建议进一步询问", "Heading2"))
    questions = data.get("suggested_questions", [])
    if questions:
        for index, question in enumerate(questions, start=1):
            parts.append(paragraph(f"{index}. {_text(question)}"))
    else:
        parts.append(paragraph("未提供"))
    append_list(parts, "边界说明", data.get("boundary_notes", []))
    return parts


def render_session_note(data):
    parts = [paragraph(data.get("title") or "本次咨询记录", "Heading1")]
    for section in data.get("sections", []):
        parts.append(paragraph(section.get("heading", "未命名栏目"), "Heading2"))
        parts.append(paragraph(section.get("content", "")))
    if data.get("next_session_focus"):
        parts.append(paragraph("下次咨询重点", "Heading2"))
        for item in data["next_session_focus"]:
            parts.append(paragraph("• " + _text(item)))
    if data.get("missing_information"):
        parts.append(paragraph("待补充信息", "Heading2"))
        for item in data["missing_information"]:
            parts.append(paragraph("• " + _text(item)))
    if data.get("boundary_notes"):
        parts.append(paragraph("边界说明", "Heading2"))
        for item in data["boundary_notes"]:
            parts.append(paragraph("• " + _text(item)))
    return parts


def render_body(data):
    document_type = data.get("document_type")
    if document_type == "intake_form":
        return render_intake_form(data)
    if document_type == "case_summary":
        return render_case_summary(data)
    if document_type == "session_note":
        return render_session_note(data)
    return [paragraph(data.get("title") or "咨询师助理文档", "Heading1")]


def build_document_xml(data):
    body = "".join(render_body(data))
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<w:document xmlns:w="{WORD_NS}">'
        f"<w:body>{body}<w:sectPr/></w:body>"
        "</w:document>"
    )


def content_types_xml():
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
</Types>"""


def package_rels_xml():
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""


def document_rels_xml():
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>"""


def styles_xml():
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="{WORD_NS}">
  <w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/></w:style>
  <w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="heading 2"/></w:style>
</w:styles>"""


def write_docx_package(output_path, document_xml):
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as package:
        package.writestr("[Content_Types].xml", content_types_xml())
        package.writestr("_rels/.rels", package_rels_xml())
        package.writestr("word/document.xml", document_xml)
        package.writestr("word/styles.xml", styles_xml())
        package.writestr("word/_rels/document.xml.rels", document_rels_xml())


def render_docx(data, output_path):
    if not isinstance(data, dict):
        return docx_failure("Input data must be a JSON object.")
    write_docx_package(output_path, build_document_xml(data))
    return docx_success(output_path)


def write_json(path, data):
    Path(path).write_text(
        json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Render counselor structured JSON as DOCX.")
    parser.add_argument("--input", required=True, help="Path to structured_output.json.")
    parser.add_argument("--output", required=True, help="Path to output .docx.")
    parser.add_argument(
        "--check-output",
        default=None,
        help="Path to docx_check.json. Defaults to output directory/docx_check.json.",
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    output_path = Path(args.output)
    check_path = Path(args.check_output) if args.check_output else output_path.with_name("docx_check.json")
    try:
        data = json.loads(Path(args.input).read_text(encoding="utf-8"))
        check = render_docx(data, output_path)
    except Exception as exc:
        check = docx_failure(str(exc))
    write_json(check_path, check)
    if check["status"] == "PASS":
        print(f"DOCX written: {output_path}")
        print(f"Check written: {check_path}")
        return 0
    print(f"DOCX render failed: {check['issues'][0]['message']}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
