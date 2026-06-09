import re


PLACEHOLDER_CHARS = "_＿—-"
PUNCTUATION_PATTERN = re.compile(r"[\s：:（）()\[\]【】{}<>《》、，,。.;；/\\|]+")


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
