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
