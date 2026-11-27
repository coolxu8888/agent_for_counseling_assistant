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


def append_list(parts, title, items, empty_text="未提供"):
    parts.append(paragraph(title, "Heading2"))
    if items:
        for item in items:
            parts.append(paragraph("• " + _text(item)))
    else:
        parts.append(paragraph(empty_text))


def _intake_clue_text(clue):
    if not isinstance(clue, dict):
        return _text(clue)
    labels = {
        "source": "来源",
        "source_type": "来源类型",
    }
    clue_id = _text(clue.get("id")).strip()
    content = _text(clue.get("content"))
    lead = f"{clue_id}：{content}" if clue_id and content else clue_id or content
    parts = [lead] if lead else []
    parts.extend(
        f"{labels.get(key, key)}：{_text(value)}"
        for key, value in clue.items()
        if key not in {"id", "content", "status"}
    )
    return "；".join(parts)


def render_intake_form(data):
    parts = [paragraph(data.get("title") or "初访信息收集表", "Title")]
    for section in data.get("sections", []):
        parts.append(paragraph(section.get("heading", "未命名栏目"), "Heading1"))
        if "content" in section:
            parts.append(paragraph(section.get("content")))
        for field in section.get("fields", []):
            parts.append(paragraph(field.get("label", field.get("id", "")), "Heading2"))
            value = field.get("value")
            parts.append(paragraph("内容：" + (_text(value) if value not in (None, "") else "待填写")))
            if field.get("notes"):
                parts.append(paragraph("备注：" + _text(field["notes"])))
            if field.get("suggested_questions"):
                parts.append(paragraph("建议提问", "IntakeLabel"))
                for index, question in enumerate(field["suggested_questions"], start=1):
                    parts.append(paragraph(f"{index}. {_text(question)}"))
            if field.get("known_clues_used"):
                parts.append(paragraph("使用的已知线索：" + _text(field["known_clues_used"])))
    parts.append(paragraph("边界说明", "Heading1"))
    for note in data.get("boundary_notes", []) or ["未提供"]:
        parts.append(paragraph("• " + _text(note)))
    if data.get("known_clues"):
        parts.append(paragraph("已提供线索", "Heading1"))
        for clue in data["known_clues"]:
            prefix = "" if isinstance(clue, dict) and _text(clue.get("id")).strip() else "• "
            parts.append(paragraph(prefix + _intake_clue_text(clue)))
    return parts


def render_initial_session_summary(data):
    parts = [paragraph(data.get("title") or "Initial interview summary", "Heading1")]
    for section in data.get("sections", []):
        parts.append(paragraph(section.get("heading", "Unnamed section"), "Heading2"))
        append_list(parts, "Known facts", section.get("known_facts", []))
        append_list(parts, "Unclear or missing", section.get("unclear_or_missing", []))
        append_list(parts, "Follow-up questions", section.get("follow_up_questions", []))
    append_list(parts, "Summary guidance", data.get("summary_guidance", []))
    append_list(parts, "Boundary notes", data.get("boundary_notes", []))
    return parts


def render_session_note_v2(data):
    parts = [paragraph(data.get("title") or "Session note", "Heading1")]
    if data.get("record_format"):
        parts.append(paragraph("Record format", "Heading2"))
        parts.append(paragraph(data.get("record_format", "")))
    for section in data.get("sections", []):
        parts.append(paragraph(section.get("heading", "Unnamed section"), "Heading2"))
        parts.append(paragraph(section.get("content", "")))
    risk_change = data.get("risk_change")
    if isinstance(risk_change, dict):
        if risk_change.get("change_documentation"):
            append_list(parts, "Risk change documentation", risk_change.get("change_documentation", []))
        if risk_change.get("follow_up_actions"):
            append_list(parts, "Risk follow-up actions", risk_change.get("follow_up_actions", []))
    if data.get("next_session_focus"):
        parts.append(paragraph("下次咨询重点", "Heading2"))
        for item in data["next_session_focus"]:
            parts.append(paragraph("- " + _text(item)))
    if data.get("missing_information"):
        parts.append(paragraph("待补充信息", "Heading2"))
        for item in data["missing_information"]:
            parts.append(paragraph("- " + _text(item)))
    if data.get("boundary_notes"):
        parts.append(paragraph("边界说明", "Heading2"))
        for item in data["boundary_notes"]:
            parts.append(paragraph("- " + _text(item)))
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


def render_case_summary(data):
    parts = [paragraph(data.get("title") or "Case background organization", "Heading1")]
    if data.get("presenting_concerns"):
        append_list(parts, "Presenting concerns", data.get("presenting_concerns", []))
    overview = data.get("case_overview")
    if isinstance(overview, dict):
        parts.append(paragraph("Case overview", "Heading2"))
        append_list(parts, "Known facts", overview.get("known_facts", []))
        append_list(parts, "Working hypotheses", overview.get("working_hypotheses", []))
        append_list(parts, "Information gaps", overview.get("information_gaps", []))
    else:
        append_list(parts, "宸茬煡浜嬪疄", data.get("known_facts", []))

    bps = data.get("bio_psycho_social", {})
    parts.append(paragraph("Biopsychosocial structure", "Heading2"))
    for heading, key in [
        ("Biological dimension", "biological"),
        ("Psychological dimension", "psychological"),
        ("Social dimension", "social"),
    ]:
        dimension = bps.get(key, {}) if isinstance(bps, dict) else {}
        if isinstance(dimension, dict):
            parts.append(paragraph(heading, "Heading2"))
            append_list(parts, "Known facts", dimension.get("known_facts", []))
            append_list(parts, "Working hypotheses", dimension.get("working_hypotheses", []))
            append_list(parts, "Information gaps", dimension.get("information_gaps", []))
            append_list(parts, "Follow-up questions", dimension.get("follow_up_questions", []))
        else:
            append_list(parts, heading, dimension or [])

    risk_formulation = data.get("risk_formulation")
    if isinstance(risk_formulation, dict):
        parts.append(paragraph("Risk formulation", "Heading2"))
        append_list(parts, "Observed clues", risk_formulation.get("observed_clues", []))
        append_list(parts, "Missing or unclear", risk_formulation.get("missing_or_unclear", []))
        append_list(parts, "Follow-up questions", risk_formulation.get("follow_up_questions", []))
    else:
        append_list(parts, "椋庨櫓淇″彿", data.get("risk_signals", []))

    if data.get("protective_factors"):
        append_list(parts, "Protective factors", data.get("protective_factors", []))
    if data.get("recommended_focus"):
        append_list(parts, "Recommended focus", data.get("recommended_focus", []))
    else:
        append_list(parts, "淇℃伅缂哄彛", data.get("information_gaps", []))
        append_list(parts, "Follow-up questions", data.get("suggested_questions", []))
    append_list(parts, "Boundary notes", data.get("boundary_notes", []))
    return parts


def render_case_conceptualization(data):
    parts = [paragraph(data.get("title") or "Case conceptualization", "Heading1")]
    parts.append(paragraph("Selected framework", "Heading2"))
    parts.append(paragraph(data.get("selected_framework", "")))
    append_list(parts, "Known facts", data.get("known_facts", []))
    append_list(parts, "Presenting patterns", data.get("presenting_patterns", []))
    append_list(parts, "Predisposing factors", data.get("predisposing_factors", []))
    append_list(parts, "Precipitating factors", data.get("precipitating_factors", []))
    append_list(parts, "Maintaining factors", data.get("maintaining_factors", []))
    append_list(parts, "Protective factors", data.get("protective_factors", []))
    append_list(parts, "Risk considerations", data.get("risk_considerations", []))
    append_list(parts, "Working hypotheses", data.get("working_hypotheses", []))
    append_list(parts, "Questions to verify", data.get("questions_to_verify", []))
    append_list(parts, "Boundary notes", data.get("boundary_notes", []))
    return parts


def render_next_session_plan(data):
    parts = [paragraph(data.get("title") or "Next session plan", "Heading1")]
    parts.append(paragraph("Selected framework", "Heading2"))
    parts.append(paragraph(data.get("selected_framework", "")))
    parts.append(paragraph("Session goal", "Heading2"))
    parts.append(paragraph(data.get("session_goal", "")))
    append_list(parts, "Focus areas", data.get("focus_areas", []))
    append_list(parts, "Planned interventions", data.get("planned_interventions", []))
    append_list(parts, "Suggested questions", data.get("suggested_questions", []))
    append_list(parts, "Risk monitoring", data.get("risk_monitoring", []))
    append_list(parts, "Between-session tasks", data.get("between_session_tasks", []))
    append_list(parts, "Do not do", data.get("do_not_do", []))
    append_list(parts, "Boundary notes", data.get("boundary_notes", []))
    return parts


def render_counseling_roadmap(data):
    parts = [paragraph(data.get("title") or "Counseling roadmap", "Heading1")]
    parts.append(paragraph("Selected framework", "Heading2"))
    parts.append(paragraph(data.get("selected_framework", "")))
    parts.append(paragraph("Overview", "Heading2"))
    parts.append(paragraph(data.get("overview", "")))
    append_list(parts, "Phases", data.get("phases", []))
    append_list(parts, "Hypotheses to verify", data.get("hypotheses_to_verify", []))
    append_list(parts, "Session focus options", data.get("session_focus_options", []))
    append_list(parts, "Risk monitoring checkpoints", data.get("risk_monitoring_checkpoints", []))
    append_list(parts, "Collaboration_referral_reminders", data.get("collaboration_referral_reminders", []))
    append_list(parts, "Missing information", data.get("missing_information", []))
    append_list(parts, "Do not do", data.get("do_not_do", []))
    append_list(parts, "Boundary notes", data.get("boundary_notes", []))
    return parts


def render_body(data):
    document_type = data.get("document_type")
    if document_type == "intake_form":
        return render_intake_form(data)
    if document_type == "initial_session_summary":
        return render_initial_session_summary(data)
    if document_type == "case_summary":
        return render_case_summary(data)
    if document_type == "session_note":
        return render_session_note_v2(data)
    if document_type == "case_conceptualization":
        return render_case_conceptualization(data)
    if document_type == "next_session_plan":
        return render_next_session_plan(data)
    if document_type == "counseling_roadmap":
        return render_counseling_roadmap(data)
    return [paragraph(data.get("title") or "咨询师助理文档", "Heading1")]


def build_document_xml(data):
    body = "".join(render_body(data))
    section_properties = "<w:sectPr/>"
    if data.get("document_type") == "intake_form":
        section_properties = (
            '<w:sectPr><w:pgSz w:w="12240" w:h="15840"/>'
            '<w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440"/>'
            "</w:sectPr>"
        )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<w:document xmlns:w="{WORD_NS}">'
        f"<w:body>{body}{section_properties}</w:body>"
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


def document_rels_xml(*, intake_layout=False):
    if not intake_layout:
        return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>"""
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rIdStyles" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>"""


def styles_xml(*, intake_layout=False):
    if not intake_layout:
        return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="{WORD_NS}">
  <w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/></w:style>
  <w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="heading 2"/></w:style>
</w:styles>"""
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="{WORD_NS}">
  <w:docDefaults>
    <w:rPrDefault><w:rPr>
      <w:rFonts w:ascii="Calibri" w:hAnsi="Calibri" w:eastAsia="Microsoft YaHei" w:cs="Calibri"/>
      <w:color w:val="000000"/><w:sz w:val="22"/><w:szCs w:val="22"/>
    </w:rPr></w:rPrDefault>
    <w:pPrDefault><w:pPr>
      <w:widowControl/>
      <w:spacing w:after="80" w:line="276" w:lineRule="auto"/>
    </w:pPr></w:pPrDefault>
  </w:docDefaults>
  <w:style w:type="paragraph" w:default="1" w:styleId="Normal">
    <w:name w:val="Normal"/><w:qFormat/>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Title">
    <w:name w:val="Title"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:qFormat/>
    <w:pPr><w:keepNext/><w:spacing w:before="0" w:after="240"/></w:pPr>
    <w:rPr><w:b/><w:color w:val="000000"/><w:sz w:val="36"/><w:szCs w:val="36"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading1">
    <w:name w:val="heading 1"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:qFormat/>
    <w:pPr><w:keepNext/><w:spacing w:before="240" w:after="100"/><w:outlineLvl w:val="0"/></w:pPr>
    <w:rPr><w:b/><w:color w:val="000000"/><w:sz w:val="30"/><w:szCs w:val="30"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading2">
    <w:name w:val="heading 2"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:qFormat/>
    <w:pPr><w:keepNext/><w:spacing w:before="160" w:after="60"/><w:outlineLvl w:val="1"/></w:pPr>
    <w:rPr><w:b/><w:color w:val="000000"/><w:sz w:val="24"/><w:szCs w:val="24"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="IntakeLabel">
    <w:name w:val="Intake label"/><w:basedOn w:val="Normal"/>
    <w:pPr><w:keepNext/><w:spacing w:before="80" w:after="40"/></w:pPr>
    <w:rPr><w:b/></w:rPr>
  </w:style>
</w:styles>"""


def write_docx_package(output_path, document_xml, *, intake_layout=False):
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as package:
        package.writestr("[Content_Types].xml", content_types_xml())
        package.writestr("_rels/.rels", package_rels_xml())
        package.writestr("word/document.xml", document_xml)
        package.writestr("word/styles.xml", styles_xml(intake_layout=intake_layout))
        package.writestr(
            "word/_rels/document.xml.rels", document_rels_xml(intake_layout=intake_layout)
        )


def render_docx(data, output_path):
    if not isinstance(data, dict):
        return docx_failure("Input data must be a JSON object.")
    write_docx_package(
        output_path, build_document_xml(data), intake_layout=data.get("document_type") == "intake_form"
    )
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
