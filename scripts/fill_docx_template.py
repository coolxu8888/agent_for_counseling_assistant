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
    load_deepseek_config,
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

STYLE_PROFILES = {
    "professional_concise": "Use concise, professional counseling-record language.",
    "warm_clinical": "Use warm, empathic, but still clinically appropriate language.",
    "institutional_record": "Use formal institutional record language with clear facts and boundaries.",
    "supervision_summary": "Use supervision-oriented language that highlights case understanding, uncertainty, and next steps.",
    "custom": "Follow the custom style instruction provided by the user.",
}
EXISTING_CONTENT_POLICIES = {"merge", "ask", "replace", "blank_only"}
DRAFT_ACTIONS = {
    "fill_blank",
    "append_to_existing",
    "revise_existing",
    "replace_existing",
    "keep_existing",
    "leave_blank",
}
DRAFT_CONFIDENCES = {"high", "medium", "low", "none"}
AUTO_FILL_CONFIDENCES = {"high", "medium"}
PROTECTED_TEMPLATE_LABELS = {"学号", "姓名", "咨询师签名", "签名", "注"}

BLOCK_SLOT_LABELS = {
    "来访者主要困扰",
    "来访者基本情况重大生活事件家庭状况人际关系状况学习状况恋爱状况等",
    "来访者认知情感行为及社会功能的基本状况",
    "来访者主要社会支持和应对方式",
    "来访者既往咨询求助史精神疾病史和就诊服药情况",
    "来访者心理测试结果",
}


def normalize_label(label):
    text = "" if label is None else str(label)
    text = PUNCTUATION_PATTERN.sub("", text)
    for char in PLACEHOLDER_CHARS:
        text = text.replace(char, "")
    return text.strip()


def is_table_block_label(text):
    normalized = normalize_label(text)
    if not normalized:
        return False
    normalized_without_number = re.sub(r"^\d+", "", normalized)
    return (
        normalized in BLOCK_SLOT_LABELS
        or normalized_without_number in BLOCK_SLOT_LABELS
        or normalized in globals().get("W1_FIXED_SUMMARY_BLOCK_LABELS", set())
    )


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


W1_SUMMARY_SECTION_ALIASES = {
    "main_distress": [
        "Main distress",
        "Main complaint",
        "Presenting concern",
        "Presenting concerns",
    ],
    "basic_situation": [
        "Basic situation",
        "Background",
        "Current situation",
        "Current stressors and background",
    ],
    "functioning": [
        "Functioning",
        "Emotion and functioning",
        "Emotional functioning",
    ],
    "support_coping": [
        "Support and coping",
        "Support system",
        "Coping resources",
    ],
    "history": [
        "Prior help-seeking and treatment history",
        "Help-seeking history",
        "Treatment history",
        "Prior counseling history",
    ],
    "psychological_tests": [
        "Psychological tests",
        "Assessment findings",
        "Psychological assessment",
    ],
    "risk_crisis": [
        "Risk and crisis information",
        "Risk and crisis",
        "Risk information",
        "Safety risk and crisis",
    ],
    "handling_suggestion": [
        "Handling suggestions",
        "Counselor handling suggestions",
        "Suggested handling",
    ],
    "other_notes": [
        "Other notes",
        "Additional notes",
    ],
}

# Stable mappings for the shipped W1 fixed-summary form. These labels are keyed
# by canonical section id so English model headings still fill the Chinese form.
W1_FIXED_SUMMARY_LABELS = {
    "main_distress": "\u6765\u8bbf\u8005\u4e3b\u8981\u56f0\u6270",
    "basic_situation": "\u6765\u8bbf\u8005\u57fa\u672c\u60c5\u51b5\uff08\u91cd\u5927\u751f\u6d3b\u4e8b\u4ef6\uff0c\u5bb6\u5ead\u72b6\u51b5\uff0c\u4eba\u9645\u5173\u7cfb\u72b6\u51b5\uff0c\u5b66\u4e60\u72b6\u51b5\uff0c\u604b\u7231\u72b6\u51b5\u7b49\uff09",
    "functioning": "\u6765\u8bbf\u8005\u8ba4\u77e5\u3001\u60c5\u611f\u3001\u884c\u4e3a\u53ca\u793e\u4f1a\u529f\u80fd\u7684\u57fa\u672c\u72b6\u51b5",
    "support_coping": "\u6765\u8bbf\u8005\u4e3b\u8981\u793e\u4f1a\u652f\u6301\u548c\u5e94\u5bf9\u65b9\u5f0f",
    "history": "\u6765\u8bbf\u8005\u65e2\u5f80\u54a8\u8be2\uff08\u6c42\u52a9\uff09\u53f2\u3001\u7cbe\u795e\u75be\u75c5\u53f2\u548c\u5c31\u8bca\u3001\u670d\u836f\u60c5\u51b5",
    "psychological_tests": "6.\u6765\u8bbf\u8005\u5fc3\u7406\u6d4b\u8bd5\u7ed3\u679c",
    "risk_crisis": "\u5371\u673a\u8bc4\u4f30\u60c5\u51b5\uff08\u81ea\u4f24\u3001\u81ea\u6740\u6216\u4f24\u5bb3\u4ed6\u4eba\u60c5\u51b5\uff09",
}
W1_FIXED_SUMMARY_BLOCK_LABELS = {
    normalize_label(label) for label in W1_FIXED_SUMMARY_LABELS.values()
}

W1_SUMMARY_BUCKET_ALIASES = {
    "known_facts": ["known facts", "documented facts", "facts"],
    "unclear_or_missing": [
        "unclear or missing",
        "missing information",
        "information gaps",
        "items to verify",
    ],
    "follow_up_questions": [
        "follow-up questions",
        "follow up questions",
        "questions to verify",
        "next questions",
    ],
}


def _w1_summary_aliases(section):
    section_id = section.get("id") or ""
    heading = section.get("heading") or section.get("title") or ""
    aliases = [heading]
    aliases.extend(W1_SUMMARY_SECTION_ALIASES.get(section_id, []))
    if section_id in W1_FIXED_SUMMARY_LABELS:
        aliases.append(W1_FIXED_SUMMARY_LABELS[section_id])
    return [alias for alias in aliases if alias]


def _add_w1_summary_entries(entries, sections):
    for index, section in enumerate(sections or []):
        base_aliases = _w1_summary_aliases(section)
        for bucket, suffixes in W1_SUMMARY_BUCKET_ALIASES.items():
            value = section.get(bucket)
            if not value:
                continue
            aliases = []
            for base_alias in base_aliases:
                aliases.append(base_alias)
                for suffix in suffixes:
                    aliases.append(f"{base_alias} {suffix}")
            _add_entry(entries, f"sections[{index}].{bucket}", value, aliases)


def build_source_map(data):
    entries = []
    if not isinstance(data, dict):
        return entries

    _add_entry(entries, "title", data.get("title"), ["标题", "文档标题", data.get("title")])
    _add_section_entries(entries, data.get("sections"))

    document_type = data.get("document_type")
    if document_type == "session_note":
        risk_change = data.get("risk_change") or {}
        _add_entry(entries, "record_format", data.get("record_format"), ["记录格式", "Record format", "SOAP", "DAP", "BIRP"])
        _add_entry(
            entries,
            "risk_change.content",
            risk_change.get("content"),
            ["风险变化", "风险评估", "自杀自伤风险", "危机风险"],
        )
        _add_entry(
            entries,
            "risk_change.change_documentation",
            risk_change.get("change_documentation"),
            ["风险变化说明", "Risk change documentation", "变化记录"],
        )
        _add_entry(
            entries,
            "risk_change.follow_up_actions",
            risk_change.get("follow_up_actions"),
            ["风险后续跟进", "Risk follow-up actions", "后续风险询问"],
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

    if document_type == "initial_session_summary":
        _add_w1_summary_entries(entries, data.get("sections"))

    _add_entry(entries, "boundary_notes", data.get("boundary_notes"), ["边界说明", "伦理边界", "注意事项"])
    return entries


_BASE_BUILD_SOURCE_MAP = build_source_map


def build_source_map(data):
    entries = _BASE_BUILD_SOURCE_MAP(data)
    if not isinstance(data, dict) or data.get("document_type") != "case_summary":
        return entries
    bps = data.get("bio_psycho_social") or {}
    overview = data.get("case_overview") or {}
    risk_formulation = data.get("risk_formulation") or {}
    _add_entry(entries, "presenting_concerns", data.get("presenting_concerns"), ["主诉", "Presenting concerns", "当前困扰"])
    _add_entry(entries, "case_overview.known_facts", overview.get("known_facts"), ["已知事实", "个案背景", "基本情况", "Known facts"])
    _add_entry(entries, "case_overview.working_hypotheses", overview.get("working_hypotheses"), ["工作假设", "Working hypotheses", "初步理解"])
    _add_entry(entries, "case_overview.information_gaps", overview.get("information_gaps"), ["信息缺口", "Information gaps", "待补充信息"])
    for dimension_key, label in [("biological", "Biological"), ("psychological", "Psychological"), ("social", "Social")]:
        dimension = bps.get(dimension_key) or {}
        if not isinstance(dimension, dict):
            continue
        _add_entry(entries, f"bio_psycho_social.{dimension_key}.known_facts", dimension.get("known_facts"), [f"{label} dimension", f"{label} known facts"])
        _add_entry(entries, f"bio_psycho_social.{dimension_key}.working_hypotheses", dimension.get("working_hypotheses"), [f"{label} working hypotheses"])
        _add_entry(entries, f"bio_psycho_social.{dimension_key}.information_gaps", dimension.get("information_gaps"), [f"{label} information gaps"])
        _add_entry(entries, f"bio_psycho_social.{dimension_key}.follow_up_questions", dimension.get("follow_up_questions"), [f"{label} follow-up questions"])
    _add_entry(entries, "protective_factors", data.get("protective_factors"), ["保护因素", "Protective factors"])
    _add_entry(entries, "risk_formulation.observed_clues", risk_formulation.get("observed_clues"), ["风险线索", "Observed clues", "风险信号"])
    _add_entry(entries, "risk_formulation.missing_or_unclear", risk_formulation.get("missing_or_unclear"), ["风险信息缺口", "Missing or unclear risk information"])
    _add_entry(entries, "risk_formulation.follow_up_questions", risk_formulation.get("follow_up_questions"), ["风险追问", "Risk follow-up questions", "后续风险询问"])
    _add_entry(entries, "recommended_focus", data.get("recommended_focus"), ["建议后续聚焦", "Recommended focus"])
    return entries


_CASE_SUMMARY_BUILD_SOURCE_MAP = build_source_map


def _extend_case_summary_split_aliases(entries, data):
    if not isinstance(data, dict) or data.get("document_type") != "case_summary":
        return entries

    overview = data.get("case_overview") or {}
    bps = data.get("bio_psycho_social") or {}
    risk_formulation = data.get("risk_formulation") or {}

    _add_entry(entries, "presenting_concerns", data.get("presenting_concerns"), ["????????????????", "?????????", "Primary concerns"])
    _add_entry(entries, "case_overview.known_facts", overview.get("known_facts"), ["?????????", "??????????????????", "Case overview known facts"])
    _add_entry(entries, "case_overview.working_hypotheses", overview.get("working_hypotheses"), ["??????????????????", "Case overview working hypotheses"])
    _add_entry(entries, "case_overview.information_gaps", overview.get("information_gaps"), ["??????????????????", "Case overview information gaps"])

    dimension_labels = {
        "biological": "?????????",
        "psychological": "?????????",
        "social": "??????????",
    }
    for dimension_key, chinese_label in dimension_labels.items():
        dimension = bps.get(dimension_key) or {}
        if not isinstance(dimension, dict):
            continue
        english_label = dimension_key.title()
        _add_entry(entries, f"bio_psycho_social.{dimension_key}.known_facts", dimension.get("known_facts"), [f"{chinese_label}?????????", f"{chinese_label}?????????", f"{english_label} known facts", f"{english_label} dimension known facts"])
        _add_entry(entries, f"bio_psycho_social.{dimension_key}.working_hypotheses", dimension.get("working_hypotheses"), [f"{chinese_label}?????????", f"{chinese_label}?????????", f"{english_label} working hypotheses", f"{english_label} dimension working hypotheses"])
        _add_entry(entries, f"bio_psycho_social.{dimension_key}.information_gaps", dimension.get("information_gaps"), [f"{chinese_label}?????????", f"{chinese_label}???????????", f"{english_label} information gaps", f"{english_label} dimension information gaps"])
        _add_entry(entries, f"bio_psycho_social.{dimension_key}.follow_up_questions", dimension.get("follow_up_questions"), [f"{chinese_label}?????????", f"{chinese_label}????????????????", f"{english_label} follow-up questions", f"{english_label} dimension follow-up questions"])

    _add_entry(entries, "protective_factors", data.get("protective_factors"), ["????????????????", "Protective factors"])
    _add_entry(entries, "risk_formulation.observed_clues", risk_formulation.get("observed_clues"), ["?????????????????????", "Risk observed clues"])
    _add_entry(entries, "risk_formulation.missing_or_unclear", risk_formulation.get("missing_or_unclear"), ["??????????????", "Risk information gaps"])
    _add_entry(entries, "risk_formulation.follow_up_questions", risk_formulation.get("follow_up_questions"), ["??????????????", "Risk follow-up questions"])
    _add_entry(entries, "recommended_focus", data.get("recommended_focus"), ["??????????????", "??????????????????", "Recommended focus"])
    return entries
    return entries


def build_source_map(data):
    entries = _CASE_SUMMARY_BUILD_SOURCE_MAP(data)
    return _extend_case_summary_split_aliases(entries, data)


_W3_TEMPLATE_BUILD_SOURCE_MAP = build_source_map


def _extend_session_note_template_aliases(entries, data):
    if not isinstance(data, dict) or data.get("document_type") != "session_note":
        return entries

    risk_change = data.get("risk_change") or {}
    _add_entry(entries, "record_format", data.get("record_format"), ["Record format", "记录格式", "SOAP", "DAP", "BIRP"])
    _add_entry(entries, "risk_change.content", risk_change.get("content"), ["Risk current status", "Current risk status", "风险现状"])
    _add_entry(entries, "risk_change.change_documentation", risk_change.get("change_documentation"), ["Risk change", "Risk change documentation", "风险变化"])
    _add_entry(entries, "risk_change.follow_up_actions", risk_change.get("follow_up_actions"), ["Risk follow-up actions", "Risk follow up", "风险后续跟进"])
    _add_entry(entries, "next_session_focus", data.get("next_session_focus"), ["Next session focus", "Next-session focus", "Follow-up plan", "下次咨询重点"])
    _add_entry(entries, "boundary_notes", data.get("boundary_notes"), ["Boundary notes", "边界说明", "注意事项"])
    return entries


def build_source_map(data):
    entries = _W3_TEMPLATE_BUILD_SOURCE_MAP(data)
    return _extend_session_note_template_aliases(entries, data)


_W4_TEMPLATE_BUILD_SOURCE_MAP = build_source_map


def _extend_case_conceptualization_template_aliases(entries, data):
    if not isinstance(data, dict) or data.get("document_type") != "case_conceptualization":
        return entries

    aliases = {
        "selected_framework": ["Selected framework", "Framework", "理论取向", "概念化框架"],
        "known_facts": ["Known facts", "已知事实"],
        "presenting_patterns": ["Presenting patterns", "问题模式", "呈现模式"],
        "predisposing_factors": ["Predisposing factors", "易感因素"],
        "precipitating_factors": ["Precipitating factors", "诱发因素"],
        "maintaining_factors": ["Maintaining factors", "维持因素"],
        "protective_factors": ["Protective factors", "保护因素"],
        "risk_considerations": ["Risk considerations", "风险考虑", "风险线索"],
        "working_hypotheses": ["Working hypotheses", "工作假设", "概念化假设"],
        "questions_to_verify": ["Questions to verify", "待核实问题", "需要核实的问题"],
        "boundary_notes": ["Boundary notes", "边界说明", "注意事项"],
    }
    for key, labels in aliases.items():
        _add_entry(entries, key, data.get(key), labels)
    return entries


def build_source_map(data):
    entries = _W4_TEMPLATE_BUILD_SOURCE_MAP(data)
    return _extend_case_conceptualization_template_aliases(entries, data)


_W5_TEMPLATE_BUILD_SOURCE_MAP = build_source_map


def _extend_next_session_plan_template_aliases(entries, data):
    if not isinstance(data, dict) or data.get("document_type") != "next_session_plan":
        return entries

    aliases = {
        "selected_framework": ["Selected framework", "Framework", "理论框架", "框架选择", "咨询框架"],
        "session_goal": ["Session goal", "会话目标", "会谈目标", "下次咨询目标"],
        "focus_areas": ["Focus areas", "焦点领域", "重点关注领域", "关注领域"],
        "planned_interventions": ["Planned interventions", "建议的干预", "干预方向", "干预方式"],
        "suggested_questions": ["Suggested questions", "建议提问", "探索性问题", "建议探索的问题"],
        "risk_monitoring": ["Risk monitoring", "风险检查点", "风险监测", "风险监控"],
        "between_session_tasks": ["Between-session tasks", "Between session tasks", "会话间任务", "会谈间任务", "可选任务"],
        "do_not_do": ["Do not do", "不做什么", "不进行", "不替代", "不扩展"],
        "boundary_notes": ["Boundary notes", "边界说明", "专业边界提醒", "注意事项"],
    }
    for key, labels in aliases.items():
        _add_entry(entries, key, data.get(key), labels)
    return entries


def build_source_map(data):
    entries = _W5_TEMPLATE_BUILD_SOURCE_MAP(data)
    return _extend_next_session_plan_template_aliases(entries, data)


_W6_TEMPLATE_BUILD_SOURCE_MAP = build_source_map


def _extend_counseling_roadmap_template_aliases(entries, data):
    if not isinstance(data, dict) or data.get("document_type") != "counseling_roadmap":
        return entries

    aliases = {
        "selected_framework": ["Selected framework", "Framework", "\u7406\u8bba\u6846\u67b6", "\u6846\u67b6\u9009\u62e9", "\u54a8\u8be2\u6846\u67b6"],
        "overview": ["Overview", "\u8def\u7ebf\u56fe\u6982\u89c8", "\u6574\u4f53\u6982\u89c8", "\u6982\u8ff0"],
        "phases": ["Phases", "\u9636\u6bb5", "\u9636\u6bb5\u5b89\u6392", "\u8def\u7ebf\u56fe\u9636\u6bb5"],
        "hypotheses_to_verify": ["Hypotheses to verify", "\u5f85\u9a8c\u8bc1\u5047\u8bbe", "\u9700\u8981\u9a8c\u8bc1\u7684\u5047\u8bbe"],
        "session_focus_options": ["Session focus options", "\u4f1a\u8bdd\u7126\u70b9\u9009\u9879", "\u4f1a\u8c08\u805a\u7126\u9009\u9879", "\u5de5\u4f5c\u7126\u70b9"],
        "risk_monitoring_checkpoints": ["Risk monitoring checkpoints", "\u98ce\u9669\u76d1\u6d4b\u68c0\u67e5\u70b9", "\u98ce\u9669\u76d1\u63a7\u68c0\u67e5\u70b9", "\u98ce\u9669\u76d1\u6d4b\u8282\u70b9"],
        "collaboration_or_referral_reminders": ["Collaboration or referral reminders", "\u534f\u4f5c\u6216\u8f6c\u4ecb\u63d0\u9192", "\u534f\u4f5c\u4e0e\u8f6c\u4ecb\u63d0\u9192", "\u5408\u4f5c/\u8f6c\u4ecb\u63d0\u9192"],
        "missing_information": ["Missing information", "\u5f85\u8865\u5145\u4fe1\u606f", "\u7f3a\u5931\u4fe1\u606f", "\u4fe1\u606f\u7f3a\u53e3"],
        "do_not_do": ["Do not do", "\u4e0d\u505a\u4ec0\u4e48", "\u660e\u786e\u7684\u4e0d\u505a\u8fb9\u754c", "\u4e0d\u8fdb\u884c", "\u4e0d\u66ff\u4ee3"],
        "boundary_notes": ["Boundary notes", "\u8fb9\u754c\u8bf4\u660e", "\u91cd\u8981\u8fb9\u754c\u8bf4\u660e", "\u4e13\u4e1a\u8fb9\u754c\u63d0\u9192"],
    }
    for key, labels in aliases.items():
        _add_entry(entries, key, data.get(key), labels)
    return entries


def build_source_map(data):
    entries = _W6_TEMPLATE_BUILD_SOURCE_MAP(data)
    return _extend_counseling_roadmap_template_aliases(entries, data)


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
            "Common bounded planning labels such as 咨询目标, 后续目标, or 后续计划 can map to next_session_focus or recommended_focus when the structured source clearly contains counselor follow-up focus rather than diagnosis or a multi-session treatment plan.",
        ],
        "examples": [
            {
                "template_label": "咨询目标",
                "preferred_source_path": "next_session_focus",
                "when": "The structured source contains bounded follow-up focus or the next-session target.",
            }
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


def build_template_draft_prompt(slots, raw_input, style, custom_style, existing_content_policy):
    style = style if style in STYLE_PROFILES else "professional_concise"
    existing_content_policy = (
        existing_content_policy
        if existing_content_policy in EXISTING_CONTENT_POLICIES
        else "merge"
    )
    prompt_slots = []
    for slot in slots:
        prompt_slot = dict(slot)
        if prompt_slot.get("slot_type") == "table_block_cell" and normalize_label(prompt_slot.get("current_text")) == normalize_label(prompt_slot.get("label")):
            prompt_slot["current_text"] = ""
            prompt_slot["current_text_note"] = "This is a structural section heading; treat it as blank fillable space below the heading."
        prompt_slots.append(prompt_slot)

    prompt_package = {
        "task": "Draft safe field-level content for a counselor Word template. Return JSON only.",
        "language": "Chinese unless the source material clearly requires another language.",
        "style": {
            "selected": style,
            "instruction": STYLE_PROFILES[style],
            "custom_style": custom_style or "",
        },
        "existing_content_policy": existing_content_policy,
        "policy_meanings": {
            "merge": "Preserve existing content; append or lightly revise only when raw material adds useful supported information.",
            "ask": "Do not overwrite non-empty fields. Use keep_existing for non-empty slots and explain needed confirmation.",
            "replace": "May replace recognizable existing field content when raw material supports a better organized version.",
            "blank_only": "Fill only blank placeholders. Keep all non-empty slots unchanged.",
        },
        "rules": [
            "Return JSON only. Do not wrap in Markdown unless unavoidable.",
            "Use only slot_id values from template_slots.",
            "Do not invent facts not present in raw_material or current_text.",
            "Do not produce a final psychiatric diagnosis unless the material explicitly says a qualified professional already made it.",
            "Do not produce a final self-harm or violence risk level as a clinical determination.",
            "Do not fill identity, contact, medical, medication, emergency contact, or test result fields unless explicitly present.",
            "If source material is vague or absent for a slot, use leave_blank or keep_existing.",
            "For risk content, preserve uncertainty and recommend counselor assessment instead of making final judgments.",
            "Use high or medium confidence only when evidence directly supports the content.",
        ],
        "allowed_actions": sorted(DRAFT_ACTIONS),
        "allowed_confidences": sorted(DRAFT_CONFIDENCES),
        "response_schema": {
            "drafts": [
                {
                    "slot_id": "string from template_slots",
                    "template_label": "string",
                    "action": "fill_blank|append_to_existing|revise_existing|replace_existing|keep_existing|leave_blank",
                    "content": "field content, empty only for keep_existing or leave_blank",
                    "confidence": "high|medium|low|none",
                    "evidence": ["short quote or paraphrase from raw material/current text"],
                    "reason": "brief reason",
                }
            ],
            "global_warnings": ["brief warning"],
        },
        "template_slots": prompt_slots,
        "raw_material": raw_input or "",
    }
    return (
        "You are a constrained counseling-document drafting assistant. Return JSON only.\n"
        + json.dumps(prompt_package, ensure_ascii=False, indent=2, sort_keys=True)
    )


def extract_template_draft_json(answer_text):
    text = (answer_text or "").strip()
    blocks = re.findall(r"```json\s*(.*?)\s*```", text, flags=re.IGNORECASE | re.DOTALL)
    candidate = blocks[-1].strip() if blocks else text
    return json.loads(candidate)


def _draft_item(slot, action, content, confidence, reason, evidence=None):
    return {
        "slot_id": slot.get("slot_id", ""),
        "template_label": slot.get("label", ""),
        "action": action,
        "content": content or "",
        "confidence": confidence,
        "evidence": evidence or [],
        "reason": reason,
    }


def slot_has_existing_content(slot):
    if slot.get("slot_type") == "table_block_cell" and normalize_label(slot.get("current_text")) == normalize_label(slot.get("label")):
        return False
    return not is_placeholder_text(slot.get("current_text", ""))


def validate_template_draft(raw_draft, slots, existing_content_policy):
    existing_content_policy = (
        existing_content_policy
        if existing_content_policy in EXISTING_CONTENT_POLICIES
        else "merge"
    )
    slots_by_id = {slot.get("slot_id"): slot for slot in slots}
    validated = {"drafts": [], "global_warnings": [], "issues": []}

    if isinstance(raw_draft, dict):
        for warning in raw_draft.get("global_warnings", []) or []:
            if warning:
                validated["global_warnings"].append(str(warning))

    draft_items = (raw_draft or {}).get("drafts", []) if isinstance(raw_draft, dict) else []
    for raw_item in draft_items:
        slot_id = raw_item.get("slot_id")
        slot = slots_by_id.get(slot_id)
        if not slot:
            validated["issues"].append(
                {
                    "level": "WARN",
                    "message": "Dropped draft for unknown slot_id.",
                    "slot_id": slot_id,
                }
            )
            continue

        action = raw_item.get("action", "leave_blank")
        if action not in DRAFT_ACTIONS:
            action = "leave_blank"
        confidence = raw_item.get("confidence", "none")
        if confidence not in DRAFT_CONFIDENCES:
            confidence = "none"
        content = render_value(raw_item.get("content", "")).strip()
        evidence = raw_item.get("evidence", [])
        if not isinstance(evidence, list):
            evidence = [str(evidence)]
        reason = raw_item.get("reason", "Model draft.")
        has_existing = slot_has_existing_content(slot)
        normalized_label = normalize_label(raw_item.get("template_label") or slot.get("label", ""))

        if confidence not in AUTO_FILL_CONFIDENCES and action not in {"keep_existing", "leave_blank"}:
            action = "leave_blank"
            content = ""
            reason = f"Skipped low-confidence draft. Original reason: {reason}"
        if not content and action not in {"keep_existing", "leave_blank"}:
            action = "leave_blank"
            reason = f"Skipped empty draft. Original reason: {reason}"
        if existing_content_policy == "blank_only" and has_existing and action != "keep_existing":
            action = "keep_existing"
            content = ""
            reason = "Existing content policy is blank_only; non-empty slot preserved."
        elif existing_content_policy == "ask" and has_existing and action != "keep_existing":
            action = "keep_existing"
            content = ""
            reason = "Existing content policy is ask; non-empty slot requires user confirmation."
        elif existing_content_policy != "replace" and action == "replace_existing":
            action = "append_to_existing" if has_existing and content else "fill_blank"
            reason = "replace_existing is not allowed by the selected policy; downgraded safely."
        elif not has_existing and action in {"append_to_existing", "revise_existing", "replace_existing"}:
            action = "fill_blank"
        if any(protected == normalized_label or protected in normalized_label for protected in PROTECTED_TEMPLATE_LABELS):
            if action not in {"keep_existing", "leave_blank"}:
                action = "keep_existing" if has_existing else "leave_blank"
                content = ""
                reason = "Protected identity/signature/note field preserved for manual review."

        validated["drafts"].append(
            {
                "slot_id": slot_id,
                "template_label": raw_item.get("template_label") or slot.get("label", ""),
                "action": action,
                "content": content,
                "confidence": confidence,
                "evidence": [str(item) for item in evidence if item],
                "reason": reason,
            }
        )

    return validated


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


def extract_template_slots_from_xml(document_xml, include_prefilled=False):
    root = ET.fromstring(document_xml)
    slots = []

    for table_index, table in enumerate(root.iter(TBL_TAG)):
        for row_index, row in enumerate(table.iter(TR_TAG)):
            cells = list(row.iter(TC_TAG))
            if len(cells) == 1:
                label = element_text(cells[0]).strip()
                if is_table_block_label(label):
                    location = f"table[{table_index}].row[{row_index}].cell[0]"
                    slots.append(
                        {
                            "slot_id": location,
                            "label": label,
                            "location": location,
                            "slot_type": "table_block_cell",
                            "current_text": label,
                        }
                    )
            for cell_index, cell in enumerate(cells[:-1]):
                label = element_text(cell).strip()
                target = cells[cell_index + 1]
                target_text = element_text(target)
                if label and (include_prefilled or is_placeholder_text(target_text)):
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
        parsed = _paragraph_label_and_value(text, include_prefilled=include_prefilled)
        if not parsed:
            continue
        label, _separator, _value = parsed
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


def extract_template_slots(template_path, include_prefilled=False):
    with zipfile.ZipFile(template_path, "r") as package:
        if "word/document.xml" not in package.namelist():
            raise ValueError("DOCX template is missing word/document.xml.")
        return extract_template_slots_from_xml(
            package.read("word/document.xml"),
            include_prefilled=include_prefilled,
        )


def _slot_targets(root, include_prefilled=False):
    targets = {}
    for table_index, table in enumerate(root.iter(TBL_TAG)):
        for row_index, row in enumerate(table.iter(TR_TAG)):
            cells = list(row.iter(TC_TAG))
            if len(cells) == 1:
                label = element_text(cells[0]).strip()
                if is_table_block_label(label):
                    location = f"table[{table_index}].row[{row_index}].cell[0]"
                    targets[location] = {
                        "element": cells[0],
                        "label": label,
                        "location": location,
                        "slot_type": "table_block_cell",
                        "current_text": label,
                    }
            for cell_index, cell in enumerate(cells[:-1]):
                label = element_text(cell).strip()
                target = cells[cell_index + 1]
                target_text = element_text(target)
                if label and (include_prefilled or is_placeholder_text(target_text)):
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
        parsed = _paragraph_label_and_value(text, include_prefilled=include_prefilled)
        if not parsed:
            continue
        label, separator, _value = parsed
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
        "drafted_fields": [],
        "kept_fields": [],
        "skipped_fields": [],
        "unfilled_fields": [],
        "global_warnings": [],
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
            if len(cells) == 1:
                label = element_text(cells[0]).strip()
                if is_table_block_label(label):
                    match = find_source_match(label, source_map)
                    if match:
                        location = f"table[{table_index}].row[{row_index}].cell[0]"
                        set_element_text(cells[0], f"{label}\n{match['value']}")
                        _record_filled(report, label, match, location)
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


def _paragraph_label_and_value(text, include_prefilled=False):
    match = re.match(r"^\s*(?P<label>[^：:Ŗē\n]{1,200})(?P<sep>[：:Ŗē]\s*)(?P<value>.*)$", text or "")
    if not match:
        return None
    value = match.group("value")
    if not include_prefilled and not is_placeholder_text(value):
        return None
    return match.group("label").strip(), match.group("sep"), value


def _paragraph_label_and_placeholder(text):
    match = re.match(r"^\s*(?P<label>[^：:\n]{1,200})(?P<sep>[：:]\s*)(?P<value>.*)$", text or "")
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
        if (
            not is_placeholder_text(current_text)
            and target["slot_type"] not in {"paragraph_placeholder", "table_block_cell"}
        ):
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
        elif target["slot_type"] == "table_block_cell":
            text = f"{target['label']}\n{value}"
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


def _drafted_field_record(item, location, current_text=""):
    return {
        "template_label": item.get("template_label", ""),
        "action": item.get("action", ""),
        "confidence": item.get("confidence", "none"),
        "location": location,
        "reason": item.get("reason", ""),
        "evidence": item.get("evidence", []),
        "previous_text": current_text,
    }


def _text_for_draft_target(target, item):
    content = item.get("content", "")
    action = item.get("action")
    current_text = element_text(target["element"])
    if action == "append_to_existing" and not is_placeholder_text(current_text):
        text = f"{current_text.rstrip()}\n{content}"
    else:
        text = content

    if target["slot_type"] == "paragraph_placeholder":
        if action == "append_to_existing" and not is_placeholder_text(current_text):
            return text
        return f"{target['label']}{target.get('separator', '：')}{text}"
    if target["slot_type"] == "table_block_cell":
        if action == "append_to_existing" and not is_placeholder_text(current_text):
            return text
        return f"{target['label']}\n{text}"
    return text


def target_has_existing_content(target):
    if target.get("slot_type") == "table_block_cell" and normalize_label(element_text(target["element"])) == normalize_label(target.get("label", "")):
        return False
    return not is_placeholder_text(element_text(target["element"]))


def fill_slots_by_draft(root, draft, report, existing_content_policy="merge"):
    targets = _slot_targets(root, include_prefilled=True)
    for item in draft.get("drafts", []):
        slot_id = item.get("slot_id")
        target = targets.get(slot_id)
        if not target:
            report["skipped_fields"].append(
                {
                    "template_label": item.get("template_label", ""),
                    "action": item.get("action", ""),
                    "reason": "Draft slot was not found in the template.",
                    "location": slot_id,
                }
            )
            continue

        action = item.get("action", "leave_blank")
        current_text = element_text(target["element"])
        if action == "keep_existing":
            report["kept_fields"].append(_drafted_field_record(item, slot_id, current_text))
            continue
        if action == "leave_blank":
            report["skipped_fields"].append(
                {
                    **_drafted_field_record(item, slot_id, current_text),
                    "reason": item.get("reason", "Draft chose to leave this field blank."),
                }
            )
            continue

        if existing_content_policy in {"ask", "blank_only"} and target_has_existing_content(target):
            report["kept_fields"].append(
                {
                    **_drafted_field_record(item, slot_id, current_text),
                    "reason": f"Existing content policy is {existing_content_policy}; non-empty slot preserved.",
                }
            )
            continue

        text = _text_for_draft_target(target, item)
        set_element_text(target["element"], text)
        record = _drafted_field_record(item, slot_id, current_text)
        report["drafted_fields"].append(record)
        report["filled_fields"].append(
            {
                "template_label": item.get("template_label", target.get("label", "")),
                "source_path": "template_draft",
                "confidence": item.get("confidence", "medium"),
                "location": slot_id,
                "action": action,
            }
        )


def fill_document_xml_from_draft(document_xml, draft, report, existing_content_policy="merge"):
    root = ET.fromstring(document_xml)
    fill_slots_by_draft(root, draft, report, existing_content_policy=existing_content_policy)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


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


def _fill_docx_template_loaded(template_path, structured_label, output_path, report_path, data, mapping=None):
    template = Path(template_path)
    output = Path(output_path)
    report = _base_report(template, structured_label, output)

    try:
        with zipfile.ZipFile(template, "r") as source_package:
            if "word/document.xml" not in source_package.namelist():
                report = report_failure("DOCX template is missing word/document.xml.", template, structured_label, output)
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
        report = report_failure(str(exc), template, structured_label, output)

    write_report(report_path, report)
    return report


def fill_docx_template(template_path, structured_path, output_path, report_path, mapping_path=None):
    structured = Path(structured_path)
    try:
        data = json.loads(structured.read_text(encoding="utf-8"))
        mapping = json.loads(Path(mapping_path).read_text(encoding="utf-8")) if mapping_path else None
    except Exception as exc:
        report = report_failure(str(exc), template_path, structured, output_path)
        write_report(report_path, report)
        return report

    return _fill_docx_template_loaded(
        template_path,
        structured,
        output_path,
        report_path,
        data,
        mapping=mapping,
    )


def fill_docx_template_with_llm_mapping(
    template_path,
    structured_path,
    output_path,
    report_path,
    mapping_output_path=None,
    config=None,
    http_post_json=post_json,
):
    template = Path(template_path)
    structured = Path(structured_path)
    try:
        data = json.loads(structured.read_text(encoding="utf-8"))
        slots = extract_template_slots(template)
        source_paths = build_source_paths(data)
        base_mapping = build_template_mapping(slots, source_paths)
        llm_result = run_deepseek_template_mapping(
            base_mapping,
            source_paths,
            config or load_deepseek_config(),
            http_post_json=http_post_json,
        )
        mapping = dict(llm_result["mapping"])
        mapping["llm_status"] = llm_result["llm_status"]
        if llm_result["llm_issues"]:
            mapping["llm_issues"] = llm_result["llm_issues"]
        if mapping_output_path:
            write_json_file(mapping_output_path, mapping)
        report = _fill_docx_template_loaded(
            template,
            structured,
            output_path,
            report_path,
            data,
            mapping=llm_result["mapping"],
        )
    except Exception as exc:
        report = report_failure(str(exc), template, structured, output_path)
        write_report(report_path, report)
        return report

    report["llm_status"] = llm_result["llm_status"]
    report["mapping_file"] = str(mapping_output_path) if mapping_output_path else ""
    if llm_result["llm_issues"]:
        report["issues"].extend(llm_result["llm_issues"])
        _finalize_report(report)
    write_report(report_path, report)
    return report


def run_deepseek_template_draft(
    slots,
    raw_input,
    style,
    custom_style,
    existing_content_policy,
    config,
    http_post_json=post_json,
):
    prompt = build_template_draft_prompt(
        slots,
        raw_input,
        style,
        custom_style,
        existing_content_policy,
    )
    payload = build_chat_payload(config.model, prompt)
    response_json = http_post_json(
        deepseek_chat_completions_url(config.base_url),
        {"Authorization": f"Bearer {config.api_key}"},
        payload,
        config.timeout_seconds,
    )
    answer_text = extract_answer_text(response_json)
    raw_draft = extract_template_draft_json(answer_text)
    return validate_template_draft(raw_draft, slots, existing_content_policy)


def fill_docx_template_from_draft(
    template_path,
    draft,
    output_path,
    report_path,
    draft_path=None,
    source_label="template_draft",
    existing_content_policy="merge",
):
    template = Path(template_path)
    output = Path(output_path)
    report = _base_report(template, source_label, output)
    report["template_draft_file"] = str(draft_path or "")
    report["existing_content_policy"] = existing_content_policy
    report["global_warnings"] = list(draft.get("global_warnings", []))
    report["issues"].extend(draft.get("issues", []))
    for warning in report["global_warnings"]:
        report["issues"].append({"level": "WARN", "message": warning})

    try:
        with zipfile.ZipFile(template, "r") as source_package:
            if "word/document.xml" not in source_package.namelist():
                report = report_failure("DOCX template is missing word/document.xml.", template, source_label, output)
            else:
                document_xml = source_package.read("word/document.xml")
                filled_xml = fill_document_xml_from_draft(
                    document_xml,
                    draft,
                    report,
                    existing_content_policy=existing_content_policy,
                )
                output.parent.mkdir(parents=True, exist_ok=True)
                with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as output_package:
                    for item in source_package.infolist():
                        content = filled_xml if item.filename == "word/document.xml" else source_package.read(item.filename)
                        output_package.writestr(item, content)
                _finalize_report(report)
    except Exception as exc:
        report = report_failure(str(exc), template, source_label, output)

    write_report(report_path, report)
    return report


def fill_docx_template_from_raw(
    template_path,
    raw_input,
    output_path,
    report_path,
    draft_path,
    style="professional_concise",
    custom_style="",
    existing_content_policy="merge",
    config=None,
    http_post_json=post_json,
):
    template = Path(template_path)
    output = Path(output_path)
    draft_output = Path(draft_path)
    report_output = Path(report_path)
    config = config or load_deepseek_config()
    slots = extract_template_slots(template, include_prefilled=True)
    draft = run_deepseek_template_draft(
        slots,
        raw_input,
        style,
        custom_style,
        existing_content_policy,
        config,
        http_post_json=http_post_json,
    )
    draft_output.parent.mkdir(parents=True, exist_ok=True)
    draft_output.write_text(
        json.dumps(draft, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return fill_docx_template_from_draft(
        template,
        draft,
        output,
        report_output,
        draft_path=draft_output,
        source_label="raw_input",
        existing_content_policy=existing_content_policy,
    )


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
    parser.add_argument("--llm-map", action="store_true", help="Use DeepSeek to map unresolved slots to allowed source paths.")
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
        if args.llm_map:
            llm_result = run_deepseek_template_mapping(mapping, source_paths, load_deepseek_config())
            mapping = llm_result["mapping"]
            if llm_result["llm_status"] == "error":
                mapping.setdefault("llm_issues", []).extend(llm_result["llm_issues"])
            else:
                mapping["llm_status"] = llm_result["llm_status"]

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
