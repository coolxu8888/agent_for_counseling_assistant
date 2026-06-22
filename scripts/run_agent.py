import argparse
import json
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from clean_eval_outputs import run_dimension_rubric, run_rule_checks
from run_model_eval import (
    build_chat_payload,
    deepseek_chat_completions_url,
    extract_answer_text,
    load_deepseek_config,
    post_json,
)
from render_docx import docx_failure, render_docx


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RETRIEVAL_MAP = ROOT / "rag" / "retrieval-map.v0.1.json"
DEFAULT_RUN_ROOT = ROOT / "agent-runs"
DEFAULT_RAG_ROOT = ROOT / "rag"
LOCAL_TIMEZONE = timezone(timedelta(hours=8))


class AgentInputError(ValueError):
    pass


class AgentRunError(RuntimeError):
    pass


@dataclass(frozen=True)
class WorkflowSpec:
    workflow_id: str
    workflow_key: str
    name: str
    eval_id: str
    completion_marker: str


@dataclass(frozen=True)
class AgentRunResult:
    workflow_id: str
    status: str
    run_dir: Path


WORKFLOWS = {
    "W1": WorkflowSpec(
        workflow_id="W1",
        workflow_key="workflow_1_intake_form",
        name="初访信息收集表生成",
        eval_id="W1-001",
        completion_marker="AGENT_DONE_W1",
    ),
    "W2": WorkflowSpec(
        workflow_id="W2",
        workflow_key="workflow_2_case_summary",
        name="个案信息整理",
        eval_id="W2-001",
        completion_marker="AGENT_DONE_W2",
    ),
    "W3": WorkflowSpec(
        workflow_id="W3",
        workflow_key="workflow_3_session_note",
        name="Session 总结与咨询记录生成",
        eval_id="W3-001",
        completion_marker="AGENT_DONE_W3",
    ),
    "W4": WorkflowSpec(
        workflow_id="W4",
        workflow_key="workflow_4_case_conceptualization",
        name="Case conceptualization by framework",
        eval_id="W4-001",
        completion_marker="AGENT_DONE_W4",
    ),
    "W5": WorkflowSpec(
        workflow_id="W5",
        workflow_key="workflow_5_next_session_plan",
        name="Next-session plan",
        eval_id="W5-001",
        completion_marker="AGENT_DONE_W5",
    ),
    "W6": WorkflowSpec(
        workflow_id="W6",
        workflow_key="workflow_6_counseling_roadmap",
        name="Counseling roadmap",
        eval_id="W6-001",
        completion_marker="AGENT_DONE_W6",
    ),
}

WORKFLOW_ALIASES = {
    "w1": "W1",
    "intake": "W1",
    "workflow_1": "W1",
    "workflow_1_intake_form": "W1",
    "w2": "W2",
    "case": "W2",
    "summary": "W2",
    "workflow_2": "W2",
    "workflow_2_case_summary": "W2",
    "w3": "W3",
    "session": "W3",
    "note": "W3",
    "workflow_3": "W3",
    "workflow_3_session_note": "W3",
    "w4": "W4",
    "conceptualization": "W4",
    "formulation": "W4",
    "framework": "W4",
    "workflow_4": "W4",
    "workflow_4_case_conceptualization": "W4",
    "w5": "W5",
    "next-session-plan": "W5",
    "next_session_plan": "W5",
    "session-plan": "W5",
    "planning": "W5",
    "workflow_5": "W5",
    "workflow_5_next_session_plan": "W5",
    "w6": "W6",
    "roadmap": "W6",
    "multi-session-plan": "W6",
    "multi_session_plan": "W6",
    "counseling-roadmap": "W6",
    "counseling_roadmap": "W6",
    "workflow_6": "W6",
    "workflow_6_counseling_roadmap": "W6",
}

OUTPUT_CONTRACTS = {
    "W1": [
        "标题：初访信息收集表（咨询师访谈版）",
        "必须包含栏目：基本信息、来访原因、当前困扰、生物-心理-社会评估、风险评估、知情同意、咨询师初步记录。",
        "风险评估必须覆盖：自伤、自杀、他伤、物质使用、现实检验、不安全环境、保护因素。",
        "隐私字段要体现最小必要原则，并提示敏感信息可按来访者愿意提供的程度填写。",
        "边界说明必须写入正文：本表不构成诊断，需结合咨询师专业判断。",
    ],
    "W2": [
        "标题：个案信息整理",
        "必须包含栏目：已知事实、主诉与当前困扰、生物维度、心理维度、社会维度、资源与保护因素、风险信号、信息缺口、建议进一步询问的问题。",
        "风险信号栏目必须说明材料中是否见到自伤、自杀、他伤、物质使用、现实检验或不安全环境信息。",
        "若材料未见明确风险信号，必须写：材料中未见明确风险信号，建议咨询师按需进一步评估。",
        "区分事实、推测和待验证内容；未提供的信息写未提供或未提及。",
    ],
    "W3": [
        "标题：本次咨询记录",
        "必须包含栏目：本次主题、来访者状态、关键内容、咨询师干预、来访者反应、风险变化、进展与阻滞、新增个案信息、咨询师判断或初步假设、待补充信息、下次咨询重点、咨询记录正文。",
        "风险变化栏目必须单独列出。若材料未提供风险相关信息，必须写：材料中未提供风险相关信息，建议咨询师按需进一步评估。",
        "未提供的观察、反应或判断不得编造，必须标注材料中未提供或待补充。",
    ],
}

OUTPUT_CONTRACTS["W3"].extend(
    [
        "If the user asks for SOAP, DAP, or BIRP, keep that counselor record format and still preserve a distinct risk-change section plus next-session focus.",
        "For stronger risk documentation, structured W3 output should include risk_change.content, risk_change.change_documentation, and risk_change.follow_up_actions whenever possible.",
    ]
)

OUTPUT_CONTRACTS["W4"] = [
    "Title: case conceptualization",
    "The output must name the selected framework and separate known facts, working hypotheses, and open questions.",
    "Include at minimum: selected framework, presenting patterns, predisposing factors, precipitating factors, maintaining factors, protective factors, risk considerations, working hypotheses, and questions to verify.",
    "Use tentative language such as may, possible, working hypothesis, and needs verification. Do not output deterministic diagnosis.",
    "The output may suggest framework-consistent directions for exploration, but must not become a full treatment plan or a multi-session roadmap.",
    "If the user requests a specific framework such as CBT, psychodynamic, humanistic, or integrative, stay within that lens while preserving ethics and privacy boundaries.",
]

OUTPUT_CONTRACTS["W2"] = [
    "Title: case background organization.",
    "Include at minimum: presenting concerns, case overview, biopsychosocial structure, protective factors, risk formulation, recommended focus, and boundary notes.",
    "The biopsychosocial structure must separate biological, psychological, and social dimensions, and each dimension must split known facts, working hypotheses, information gaps, and follow-up questions.",
    "Risk formulation must stay bounded to observed clues, missing or unclear risk information, and counselor-facing follow-up questions. Do not output a final diagnosis or final risk rating.",
    "Keep facts, working hypotheses, and missing information clearly separated. If information is not provided, state that it is missing or still needs verification.",
]

OUTPUT_CONTRACTS["W5"] = [
    "Title: next-session plan",
    "Generate a bounded plan for one upcoming counseling session only, not a treatment plan or multi-session roadmap.",
    "Include at minimum: selected framework, session goal, focus areas, planned interventions, suggested questions, risk monitoring, between-session tasks, and do-not-do boundaries.",
    "If a framework is named, keep the plan consistent with that framework. If no framework is named, use generic counselor-facing planning language.",
    "Use tentative, counselor-facing wording. Do not output deterministic diagnosis, final risk grading, or prescriptive crisis handling decisions.",
    "Between-session tasks must remain optional, proportionate, and safe; do not assign risky homework, exposure tasks, or multi-week programs unless the user explicitly provided them.",
]

STRUCTURED_OUTPUT_CONTRACTS = {
    "W1": {
        "workflow": "W1",
        "document_type": "intake_form",
        "title": "初访信息收集表",
        "sections": [
            {
                "id": "risk",
                "heading": "风险评估",
                "fields": [
                    {
                        "id": "suicide_ideation",
                        "label": "自杀意念",
                        "value": "",
                        "required": False,
                        "sensitive": True,
                        "risk_signal": True,
                        "notes": "可按来访者愿意提供的程度填写",
                    }
                ],
            }
        ],
        "boundary_notes": ["本表不构成诊断，需结合咨询师专业判断。"],
    },
    "W2": {
        "workflow": "W2",
        "document_type": "case_summary",
        "title": "个案信息整理",
        "known_facts": [],
        "bio_psycho_social": {
            "biological": [],
            "psychological": [],
            "social": [],
        },
        "risk_signals": [],
        "information_gaps": [],
        "suggested_questions": [],
        "boundary_notes": ["材料中未见明确风险信号时，也需建议咨询师按需进一步评估。"],
    },
    "W3": {
        "workflow": "W3",
        "document_type": "session_note",
        "title": "本次咨询记录",
        "sections": [
            {"id": "theme", "heading": "本次主题", "content": ""},
            {"id": "client_status", "heading": "来访者状态", "content": ""},
            {"id": "intervention", "heading": "咨询师干预", "content": ""},
            {"id": "risk_change", "heading": "风险变化", "content": ""},
            {"id": "next_session_focus", "heading": "下次咨询重点", "content": ""},
        ],
        "risk_change": {"content": ""},
        "next_session_focus": [],
        "missing_information": [],
        "boundary_notes": ["本记录不替代咨询师专业判断。"],
    },
}

STRUCTURED_OUTPUT_CONTRACTS["W3"]["record_format"] = "generic"
STRUCTURED_OUTPUT_CONTRACTS["W3"]["risk_change"] = {
    "content": "",
    "change_documentation": [],
    "follow_up_actions": [],
}

STRUCTURED_OUTPUT_CONTRACTS["W4"] = {
    "workflow": "W4",
    "document_type": "case_conceptualization",
    "title": "Case conceptualization",
    "selected_framework": "",
    "known_facts": [],
    "presenting_patterns": [],
    "predisposing_factors": [],
    "precipitating_factors": [],
    "maintaining_factors": [],
    "protective_factors": [],
    "risk_considerations": [],
    "working_hypotheses": [],
    "questions_to_verify": [],
    "boundary_notes": [
        "This conceptualization is a working hypothesis, not a diagnosis, final risk judgment, or treatment decision."
    ],
}

STRUCTURED_OUTPUT_CONTRACTS["W2"] = {
    "workflow": "W2",
    "document_type": "case_summary",
    "title": "Case background organization",
    "presenting_concerns": [],
    "case_overview": {
        "known_facts": [],
        "working_hypotheses": [],
        "information_gaps": [],
    },
    "bio_psycho_social": {
        "biological": {
            "known_facts": [],
            "working_hypotheses": [],
            "information_gaps": [],
            "follow_up_questions": [],
        },
        "psychological": {
            "known_facts": [],
            "working_hypotheses": [],
            "information_gaps": [],
            "follow_up_questions": [],
        },
        "social": {
            "known_facts": [],
            "working_hypotheses": [],
            "information_gaps": [],
            "follow_up_questions": [],
        },
    },
    "protective_factors": [],
    "risk_formulation": {
        "observed_clues": [],
        "missing_or_unclear": [],
        "follow_up_questions": [],
    },
    "recommended_focus": [],
    "boundary_notes": [
        "This is a counselor-facing case background organizer, not a diagnosis, final risk rating, or treatment decision."
    ],
}

STRUCTURED_OUTPUT_CONTRACTS["W5"] = {
    "workflow": "W5",
    "document_type": "next_session_plan",
    "title": "Next session plan",
    "selected_framework": "generic",
    "session_goal": "",
    "focus_areas": [],
    "planned_interventions": [],
    "suggested_questions": [],
    "risk_monitoring": [],
    "between_session_tasks": [],
    "do_not_do": [],
    "boundary_notes": [
        "This is a bounded plan for one upcoming session, not a diagnosis, final risk judgment, or full treatment plan."
    ],
}

OUTPUT_CONTRACTS["W6"] = [
    "Title: counseling roadmap",
    "Generate a bounded counselor-facing roadmap across multiple possible sessions or phases, not a fixed-duration treatment prescription.",
    "Include at minimum: selected framework, overview, phased roadmap, hypotheses to verify, session focus options, risk monitoring checkpoints, collaboration or referral reminders, missing information, and do-not-do boundaries.",
    "If a framework is named, keep the roadmap consistent with that framework. If no framework is named, use generic counselor-facing planning language.",
    "Use tentative, collaborative wording. Do not output deterministic diagnosis, guaranteed outcomes, rigid timelines, final risk grading, or prescriptive crisis handling decisions.",
    "The roadmap should stay revisable as new information emerges. Do not present a 12-session protocol, mandatory homework sequence, or fixed course length unless the user explicitly provided that context.",
]

STRUCTURED_OUTPUT_CONTRACTS["W6"] = {
    "workflow": "W6",
    "document_type": "counseling_roadmap",
    "title": "Counseling roadmap",
    "selected_framework": "generic",
    "overview": "",
    "phases": [
        {
            "phase_name": "",
            "goals": [],
            "markers_to_monitor": [],
        }
    ],
    "hypotheses_to_verify": [],
    "session_focus_options": [],
    "risk_monitoring_checkpoints": [],
    "collaboration_referral_reminders": [],
    "missing_information": [],
    "do_not_do": [],
    "boundary_notes": [
        "This roadmap is a bounded, revisable planning aid for the counselor. It is not a diagnosis, fixed treatment prescription, final risk judgment, or guaranteed outcome."
    ],
}

W1_INITIAL_INTERVIEW_SECTIONS = [
    {
        "id": "main_distress",
        "heading": "来访者主要困扰",
        "fields": [
            {
                "id": "main_distress",
                "label": "来访者主要困扰",
                "value": "",
                "required": True,
                "sensitive": False,
                "risk_signal": False,
                "notes": "记录来访者本次最主要的困扰、主诉和希望解决的问题；未提供时写未提供或待补充。",
            }
        ],
    },
    {
        "id": "basic_situation",
        "heading": "来访者基本情况（重大生活事件，家庭状况，人际关系状况，学习状况，恋爱状况等）",
        "fields": [
            {
                "id": "basic_situation",
                "label": "来访者基本情况",
                "value": "",
                "required": False,
                "sensitive": True,
                "risk_signal": False,
                "notes": "按最小必要原则整理重大生活事件、家庭、人际、学习、恋爱等信息。",
            }
        ],
    },
    {
        "id": "functioning",
        "heading": "来访者认知、情感、行为及社会功能的基本状况",
        "fields": [
            {
                "id": "functioning",
                "label": "来访者认知、情感、行为及社会功能的基本状况",
                "value": "",
                "required": False,
                "sensitive": False,
                "risk_signal": False,
                "notes": "区分材料中已提供的观察、来访者自述和待补充信息。",
            }
        ],
    },
    {
        "id": "support_coping",
        "heading": "来访者主要社会支持和应对方式",
        "fields": [
            {
                "id": "support_coping",
                "label": "来访者主要社会支持和应对方式",
                "value": "",
                "required": False,
                "sensitive": False,
                "risk_signal": False,
                "notes": "整理朋友、家人、学校或其他支持资源，以及已有应对方式。",
            }
        ],
    },
    {
        "id": "history",
        "heading": "来访者既往咨询（求助）史、精神疾病史和就诊、服药情况",
        "fields": [
            {
                "id": "history",
                "label": "来访者既往咨询（求助）史、精神疾病史和就诊、服药情况",
                "value": "",
                "required": False,
                "sensitive": True,
                "risk_signal": False,
                "notes": "仅整理材料中明确提供的信息；不得推断诊断或用药。",
            }
        ],
    },
    {
        "id": "psychological_tests",
        "heading": "来访者心理测试结果",
        "fields": [
            {
                "id": "psychological_tests",
                "label": "来访者心理测试结果",
                "value": "",
                "required": False,
                "sensitive": True,
                "risk_signal": False,
                "notes": "未提供测试结果时写未提供；不得自行生成量表分数。",
            }
        ],
    },
    {
        "id": "risk_crisis",
        "heading": "风险评估/危机评估情况（自伤、自杀或伤害他人情况）",
        "fields": [
            {
                "id": "crisis_assessment",
                "label": "危机评估情况",
                "value": "",
                "required": True,
                "sensitive": True,
                "risk_signal": True,
                "notes": "覆盖自伤、自杀、他伤、现实检验、不安全环境、保护因素；不做最终风险等级判断。",
            }
        ],
    },
    {
        "id": "handling_suggestion",
        "heading": "处理建议",
        "fields": [
            {
                "id": "handling_suggestion",
                "label": "处理建议",
                "value": "",
                "required": False,
                "sensitive": False,
                "risk_signal": False,
                "notes": "给咨询师下一步收集信息、评估和机构流程层面的建议；不替代咨询师决策。",
            }
        ],
    },
    {
        "id": "other_notes",
        "heading": "其他备注",
        "fields": [
            {
                "id": "other_notes",
                "label": "其他备注",
                "value": "",
                "required": False,
                "sensitive": False,
                "risk_signal": False,
                "notes": "记录材料限制、待补充事项或咨询师需要复核的内容。",
            }
        ],
    },
]

OUTPUT_CONTRACTS["W1"].extend(
    [
        "若需要适配初始访谈表模板，必须包含：来访者主要困扰、来访者基本情况、来访者认知、情感、行为及社会功能的基本状况、来访者主要社会支持和应对方式、来访者既往咨询（求助）史、精神疾病史和就诊、服药情况、来访者心理测试结果、危机评估情况、处理建议、其他备注。",
        "初始访谈表中的危机评估情况不得输出最终风险等级，只能整理材料中已给出的风险线索和建议咨询师进一步评估的方向。",
    ]
)

STRUCTURED_OUTPUT_CONTRACTS["W1"] = {
    "workflow": "W1",
    "document_type": "intake_form",
    "title": "心理咨询初始访谈表",
    "sections": W1_INITIAL_INTERVIEW_SECTIONS,
    "boundary_notes": ["本表仅用于初访信息收集辅助，不构成诊断或最终风险判断，需结合咨询师专业判断。"],
}

# W1 has two product modes:
# 1. Default: generate a pre-intake information collection / interview guide.
# 2. Confirmed summary mode: when the counselor provides completed initial
#    interview material and asks for a summary, use the fixed initial-session
#    summary structure below. Uploaded DOCX templates are handled by the
#    independent template-filling pipeline and must not redefine W1 defaults.
OUTPUT_CONTRACTS["W1"] = [
    "标题：初访信息收集表（咨询师访谈辅助版）",
    "默认任务是帮助咨询师在初访前梳理需要了解的信息和可提问的问题，而不是把用户上传的某个 Word 模板固定成 W1 输出标准。",
    "如果用户已经明确要求生成初访前信息收集/提问辅助表，同时输入中提供了部分来访者线索（如睡眠、压力、风险提示等），必须直接使用这些已知信息预填相关栏目，并补充其余待核实问题；不要退回成纯空白模板，也不要仅仅要求用户重新提供材料。",
    "必须包含栏目：基本信息、来访原因与当前困扰、咨询目的与个人需求、生物-心理-社会信息、风险评估、知情同意与边界说明、咨询师初步记录。",
    "字段应体现访谈中需要收集的信息、建议提问、是否敏感、是否风险相关；未知内容保持空值或写待补充，不得替咨询师编造来访者事实。",
    "如果用户直接丢来笔记或口述材料，且没有说明是要生成初访前提问表还是要总结已有初访内容，必须先追问确认。",
    "如果用户明确说明材料来自初始访谈并要求整理/总结，使用“初始访谈材料总结模式”的固定结构，不把它误认为默认初访前信息收集表。",
    "风险评估必须覆盖：自伤、自杀、他伤、物质使用、现实检验、不安全环境、保护因素；不得输出最终风险等级或替代机构危机处置。",
    "边界说明必须写入正文：本表不构成诊断、最终风险判断或治疗方案，需结合咨询师专业判断和机构流程。",
]

STRUCTURED_OUTPUT_CONTRACTS["W1"] = {
    "workflow": "W1",
    "document_type": "intake_form",
    "title": "初访信息收集表（咨询师访谈辅助版）",
    "sections": [
        {
            "id": "basic_information",
            "heading": "基本信息",
            "fields": [
                {
                    "id": "client_identifier",
                    "label": "来访者识别信息",
                    "value": "",
                    "suggested_questions": ["如何称呼来访者？是否需要记录年龄、身份或联系方式？"],
                    "required": True,
                    "sensitive": True,
                    "risk_signal": False,
                    "notes": "遵循最小必要原则，只收集本次服务所需信息。",
                }
            ],
        },
        {
            "id": "presenting_concern",
            "heading": "来访原因与当前困扰",
            "fields": [
                {
                    "id": "main_concern",
                    "label": "主要困扰/主诉",
                    "value": "",
                    "suggested_questions": ["这次最希望谈的是什么？这个困扰从什么时候开始？"],
                    "required": True,
                    "sensitive": False,
                    "risk_signal": False,
                    "notes": "记录来访者原话优先，区分事实与咨询师假设。",
                }
            ],
        },
        {
            "id": "goals_needs",
            "heading": "咨询目的与个人需求",
            "fields": [
                {
                    "id": "consulting_goals",
                    "label": "咨询期待与目标",
                    "value": "",
                    "suggested_questions": ["如果咨询有帮助，你希望首先发生什么变化？"],
                    "required": True,
                    "sensitive": False,
                    "risk_signal": False,
                    "notes": "用于帮助咨询师理解来访动机和合作目标。",
                }
            ],
        },
        {
            "id": "bio_psycho_social",
            "heading": "生物-心理-社会信息",
            "fields": [
                {
                    "id": "biological_status",
                    "label": "生物/身体状态",
                    "value": "",
                    "suggested_questions": ["近期睡眠、食欲、精力和身体健康状况如何？"],
                    "required": False,
                    "sensitive": True,
                    "risk_signal": False,
                    "notes": "仅收集与咨询目标和风险评估相关的信息。",
                },
                {
                    "id": "psychological_status",
                    "label": "情绪、认知与行为状态",
                    "value": "",
                    "suggested_questions": ["最近主要情绪、想法和行为变化是什么？"],
                    "required": False,
                    "sensitive": False,
                    "risk_signal": False,
                    "notes": "避免诊断化措辞。",
                },
                {
                    "id": "social_status",
                    "label": "家庭、人际、学习/工作与支持系统",
                    "value": "",
                    "suggested_questions": ["目前有哪些支持资源？学习、工作或家庭功能是否受影响？"],
                    "required": False,
                    "sensitive": True,
                    "risk_signal": False,
                    "notes": "关注支持资源、压力源与功能受损情况。",
                },
            ],
        },
        {
            "id": "risk_assessment",
            "heading": "风险评估",
            "fields": [
                {
                    "id": "risk_screening",
                    "label": "自伤/自杀/他伤及其他安全风险筛查",
                    "value": "",
                    "suggested_questions": ["近期是否有伤害自己、不想活、伤害他人或处于不安全环境的想法/行为？"],
                    "required": True,
                    "sensitive": True,
                    "risk_signal": True,
                    "notes": "不得输出最终风险等级；如出现风险线索，提示咨询师按机构流程进一步评估。",
                }
            ],
        },
        {
            "id": "consent_boundary",
            "heading": "知情同意与边界说明",
            "fields": [
                {
                    "id": "informed_consent",
                    "label": "保密例外、记录使用与服务边界",
                    "value": "",
                    "suggested_questions": ["是否已说明保密原则、保密例外、记录用途和服务边界？"],
                    "required": True,
                    "sensitive": False,
                    "risk_signal": False,
                    "notes": "本表不构成诊断、最终风险判断或治疗方案。",
                }
            ],
        },
        {
            "id": "counselor_notes",
            "heading": "咨询师初步记录",
            "fields": [
                {
                    "id": "missing_information",
                    "label": "待补充信息与后续追问",
                    "value": "",
                    "suggested_questions": ["哪些关键信息仍缺失？下次访谈需要优先追问什么？"],
                    "required": False,
                    "sensitive": False,
                    "risk_signal": False,
                    "notes": "用于咨询师访谈准备，不替代专业判断。",
                }
            ],
        },
    ],
    "boundary_notes": ["本表仅用于初访前访谈准备和信息收集辅助，不构成诊断、最终风险判断或治疗方案。"],
}

W1_INITIAL_SESSION_SUMMARY_CONTRACT = {
    "workflow": "W1",
    "document_type": "initial_session_summary",
    "title": "初始访谈材料总结",
    "sections": [
        {"id": "main_distress", "heading": "来访者主要困扰", "content": ""},
        {
            "id": "basic_situation",
            "heading": "来访者基本情况（重大生活事件、家庭状况、人际关系、学习/工作、恋爱状况等）",
            "content": "",
        },
        {"id": "functioning", "heading": "来访者认知、情感、行为及社会功能的基本状况", "content": ""},
        {"id": "support_coping", "heading": "来访者主要社会支持和应对方式", "content": ""},
        {"id": "history", "heading": "来访者既往咨询（求助）史、精神疾病史和就诊、服药情况", "content": ""},
        {"id": "psychological_tests", "heading": "来访者心理测试结果", "content": ""},
        {"id": "risk_crisis", "heading": "危机评估情况（自伤、自杀或伤害他人情况）", "content": ""},
        {"id": "handling_suggestion", "heading": "处理建议", "content": ""},
        {"id": "other_notes", "heading": "其他备注", "content": ""},
    ],
    "boundary_notes": ["仅整理用户已提供材料；未提供的信息写未提供或待补充，不输出最终诊断或最终风险等级。"],
}


W1_INITIAL_SESSION_SUMMARY_CONTRACT = {
    "workflow": "W1",
    "document_type": "initial_session_summary",
    "title": "Initial interview summary",
    "sections": [
        {"id": "main_distress", "heading": "Main distress", "known_facts": [], "unclear_or_missing": [], "follow_up_questions": []},
        {"id": "basic_situation", "heading": "Basic situation", "known_facts": [], "unclear_or_missing": [], "follow_up_questions": []},
        {"id": "functioning", "heading": "Functioning", "known_facts": [], "unclear_or_missing": [], "follow_up_questions": []},
        {"id": "support_coping", "heading": "Support and coping", "known_facts": [], "unclear_or_missing": [], "follow_up_questions": []},
        {"id": "history", "heading": "Prior help-seeking and treatment history", "known_facts": [], "unclear_or_missing": [], "follow_up_questions": []},
        {"id": "psychological_tests", "heading": "Psychological tests", "known_facts": [], "unclear_or_missing": [], "follow_up_questions": []},
        {"id": "risk_crisis", "heading": "Risk and crisis information", "known_facts": [], "unclear_or_missing": [], "follow_up_questions": []},
        {"id": "handling_suggestion", "heading": "Handling suggestions", "known_facts": [], "unclear_or_missing": [], "follow_up_questions": []},
        {"id": "other_notes", "heading": "Other notes", "known_facts": [], "unclear_or_missing": [], "follow_up_questions": []},
    ],
    "summary_guidance": [
        "known_facts may include only facts explicitly present in the initial interview notes.",
        "unclear_or_missing should capture unclear, missing, or still-unverified information.",
        "follow_up_questions should list counselor-facing follow-up questions only.",
        "The risk_crisis section must separate observed risk clues from missing risk data and next safety follow-up questions.",
    ],
    "boundary_notes": [
        "Organize only the material the counselor provided. Do not invent missing facts, final diagnoses, or final risk ratings."
    ],
}


def normalize_workflow(value):
    alias = (value or "").strip().lower()
    workflow_id = WORKFLOW_ALIASES.get(alias)
    if not workflow_id:
        accepted = "W1/intake, W2/case, W3/session, W4/conceptualization, W5/next-session-plan, W6/roadmap"
        raise AgentInputError(f"Unknown workflow `{value}`. Accepted workflows: {accepted}.")
    return WORKFLOWS[workflow_id]


def read_user_input(inline_text, input_file):
    has_inline = inline_text is not None
    has_file = input_file is not None
    if has_inline == has_file:
        raise AgentInputError("Pass exactly one of --input or --input-file.")

    if has_inline:
        text = str(inline_text).strip()
        source = "inline"
    else:
        text = Path(input_file).read_text(encoding="utf-8-sig").strip()
        source = "file"

    if not text:
        raise AgentInputError("User input is empty.")
    return source, text


def load_retrieval_map(path=DEFAULT_RETRIEVAL_MAP):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def selected_chunk_ids_for_workflow(workflow, retrieval_map):
    workflows = retrieval_map.get("workflows", {})
    workflow_config = workflows.get(workflow.workflow_key)
    if not workflow_config:
        raise AgentRunError(f"Workflow `{workflow.workflow_key}` is missing in retrieval map.")

    chunk_ids = []
    for route in workflow_config.get("intent_routes", []):
        for chunk_id in route.get("priority_chunks", []):
            if chunk_id not in chunk_ids:
                chunk_ids.append(chunk_id)
    if not chunk_ids:
        raise AgentRunError(f"No priority chunks configured for {workflow.workflow_key}.")
    return chunk_ids


def _front_matter_chunk_id(text):
    match = re.search(r"(?m)^chunk_id:\s*([A-Za-z0-9_.-]+)\s*$", text)
    return match.group(1) if match else None


def _index_rag_chunks(rag_root):
    index = {}
    for path in Path(rag_root).rglob("*.md"):
        text = path.read_text(encoding="utf-8")
        chunk_id = _front_matter_chunk_id(text)
        if chunk_id:
            index[chunk_id] = {"chunk_id": chunk_id, "path": path, "content": text}
    return index


def load_rag_chunks(chunk_ids, rag_root=DEFAULT_RAG_ROOT):
    index = _index_rag_chunks(rag_root)
    chunks = []
    missing = []
    for chunk_id in chunk_ids:
        chunk = index.get(chunk_id)
        if chunk is None:
            missing.append(chunk_id)
        else:
            chunks.append(chunk)
    if missing:
        raise AgentRunError("Missing RAG chunks: " + ", ".join(missing))
    return chunks


def build_prompt_package(workflow, user_input, rag_chunks, structured=False):
    rag_sections = []
    for chunk in rag_chunks:
        rag_sections.append(
            "\n".join(
                [
                    f"## Chunk: {chunk['chunk_id']}",
                    f"Path: {chunk['path']}",
                    "",
                    chunk["content"].strip(),
                ]
            )
        )

    parts = [
        "# 角色",
        "你是咨询师助理，帮助咨询师整理材料、生成结构化文档和标记信息缺口。你不能替代咨询师诊断、风险分级、危机处置或机构流程。",
        "# 当前 Workflow",
        f"{workflow.workflow_id}: {workflow.name}",
        "# 输出要求",
        "严格基于用户提供的材料作答。未提供的信息写“未提供”“未提及”或“待补充”。风险相关内容需要单独列出。避免确定性诊断措辞。",
        "# Workflow 固定输出结构",
        "\n".join(f"- {line}" for line in OUTPUT_CONTRACTS[workflow.workflow_id]),
    ]
    if structured:
        parts.extend(
            [
                "# 结构化 JSON 输出要求",
                "先输出给咨询师阅读的 Markdown 正文。随后输出一个 fenced JSON block，格式必须是 ```json 开头、``` 结束。JSON 必须能被 json.loads 解析，不要在 JSON 中写注释。Markdown 正文请保持简明，必须优先保证 JSON block 完整输出。",
                "JSON block 必须尽量贴合下面的字段结构；缺失信息用“未提供”“未提及”或空数组表示，不要编造。",
                "```json\n"
                + json.dumps(
                    STRUCTURED_OUTPUT_CONTRACTS[workflow.workflow_id],
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n```",
            ]
        )
        if workflow.workflow_id == "W1":
            parts.extend(
                [
                    "# W1 初始访谈材料总结模式",
                    "仅当用户明确说明输入是已经完成的初始访谈材料、笔记或口述记录，并要求整理/总结时，才使用下面结构。若无法判断用户想要“初访前提问表”还是“已有初访材料总结”，先追问确认。",
                    "```json\n"
                    + json.dumps(
                        W1_INITIAL_SESSION_SUMMARY_CONTRACT,
                        ensure_ascii=False,
                        indent=2,
                    )
                    + "\n```",
                ]
            )
        if workflow.workflow_id == "W1":
            parts.append(
                "每个 section 都必须拆成 known_facts、unclear_or_missing、follow_up_questions 三部分。known_facts 只写材料中已出现的事实；unclear_or_missing 用于标注模糊、缺失或仍需核实的信息；follow_up_questions 只写咨询师后续可继续核实的问题。"
            )
            parts.append(
                "risk_crisis section 必须明确区分：已看到的风险线索、材料中未提供或不清楚的风险信息、以及需要继续核实的安全问题。不得输出最终风险等级、诊断或替代机构危机处置决定。"
            )
        if workflow.workflow_id == "W1":
            parts.append(
                "For W1 initial_session_summary, every section must use known_facts, unclear_or_missing, and follow_up_questions. known_facts may contain only facts explicitly present in the source notes."
            )
            parts.append(
                "The risk_crisis section must separate observed risk clues, missing or unclear risk information, and counselor-facing safety follow-up questions. Do not output a final diagnosis or final risk rating."
            )
        if workflow.workflow_id == "W2":
            parts.append(
                "For W2, use the dedicated case background organization structure. Include presenting_concerns, case_overview, bio_psycho_social, protective_factors, risk_formulation, recommended_focus, and boundary_notes."
            )
            parts.append(
                "Each biopsychosocial dimension must include known_facts, working_hypotheses, information_gaps, and follow_up_questions. Keep known_facts limited to source material, mark uncertainty as working_hypotheses or information_gaps, and keep risk_formulation bounded to observed_clues, missing_or_unclear, and counselor-facing follow_up_questions."
            )
    parts.extend(
        [
            "# RAG 参考资料",
            "\n\n".join(rag_sections),
            "# 用户输入",
            user_input.strip(),
            "# 完成标记",
            f"回答末尾单独输出一行：{workflow.completion_marker}",
        ]
    )
    if structured and workflow.workflow_id == "W3":
        parts.insert(
            len(parts) - 5,
            "For W3, set record_format to generic, SOAP, DAP, or BIRP based on the user's request. Keep sections aligned with that record format while also preserving a separate risk-change section.",
        )
        parts.insert(
            len(parts) - 5,
            "For W3 risk_change, include content, change_documentation, and follow_up_actions. change_documentation should describe only observed changes or explicitly missing change data; follow_up_actions should stay counselor-facing and bounded.",
        )
    return "\n\n".join(parts)


def _isoformat(dt):
    return dt.astimezone(LOCAL_TIMEZONE).isoformat()


def create_run_dir(run_root=DEFAULT_RUN_ROOT, workflow_id="W", now=None):
    timestamp = (now or datetime.now(LOCAL_TIMEZONE)).astimezone(LOCAL_TIMEZONE)
    dirname = timestamp.strftime("%Y-%m-%d-%H%M%S") + f"-{workflow_id}"
    run_dir = Path(run_root) / dirname
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_dir


def write_json(path, data):
    Path(path).write_text(
        json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _safe_error_message(error):
    message = str(error).replace("\r", " ").replace("\n", " ")
    return message[:500]


def _redact_secret(message, secret):
    sanitized = _safe_error_message(message)
    if secret:
        sanitized = sanitized.replace(secret, "[REDACTED]")
    return sanitized


def _metadata_rag_chunks(chunks):
    return [
        {
            "chunk_id": chunk["chunk_id"],
            "path": str(chunk["path"]),
        }
        for chunk in chunks
    ]


def strip_agent_marker(text, workflow):
    lines = []
    for line in text.splitlines():
        normalized = line.strip().strip("*_` ")
        if normalized == workflow.completion_marker:
            break
        lines.append(line)
    return "\n".join(lines).strip() + "\n"


def run_safety_check(workflow, clean_answer):
    rule_result = run_rule_checks(workflow.eval_id, clean_answer)
    rubric_result = run_dimension_rubric(workflow.eval_id, clean_answer)
    return {
        "status": rule_result["status"],
        "rubric_status": rubric_result["status"],
        "missing_required": rule_result["missing_required"],
        "forbidden_hits": rule_result["forbidden_hits"],
        "issues": rubric_result["issues"],
        "dimensions": rubric_result["dimensions"],
    }


def structured_failure(workflow, message, path="structured_output"):
    return {
        "status": "FAIL",
        "workflow": workflow.workflow_id,
        "issues": [
            {
                "level": "ERROR",
                "path": path,
                "message": message,
            }
        ],
    }


def _text_before_marker(text, workflow):
    lines = []
    for line in text.splitlines():
        normalized = line.strip().strip("*_` ")
        if normalized == workflow.completion_marker:
            break
        lines.append(line)
    return "\n".join(lines)


def extract_structured_json(raw_text, workflow):
    text = _text_before_marker(raw_text, workflow)
    blocks = re.findall(r"```json\s*(.*?)\s*```", text, flags=re.IGNORECASE | re.DOTALL)
    if not blocks:
        return None, structured_failure(workflow, "No fenced JSON block found")
    block = blocks[-1]
    try:
        data = json.loads(block)
    except json.JSONDecodeError as exc:
        return None, structured_failure(workflow, f"JSON parse error: {exc}", path="json")
    return data, {"status": "PASS", "workflow": workflow.workflow_id, "issues": []}


def _structured_issue(path, message):
    return {"level": "ERROR", "path": path, "message": message}


def _json_text(data):
    return json.dumps(data, ensure_ascii=False)


def _all_fields(data):
    for section in data.get("sections", []):
        for field in section.get("fields", []):
            yield field


def _has_non_empty(data, key):
    value = data.get(key)
    return value is not None and value != [] and value != {} and value != ""


def _validate_list_field(issues, data, path, allow_empty=False):
    current = data
    for part in path.split("."):
        if not isinstance(current, dict):
            current = None
            break
        current = current.get(part)
    if current is None:
        issues.append(_structured_issue(path, f"{path} is required."))
        return
    if not isinstance(current, list):
        issues.append(_structured_issue(path, f"{path} must be a list."))
        return
    if not allow_empty and not current:
        issues.append(_structured_issue(path, f"{path} must be non-empty."))


def _validate_w2_dimension(issues, bps, dimension_name):
    dimension = bps.get(dimension_name)
    if not isinstance(dimension, dict):
        for key in ["known_facts", "working_hypotheses", "information_gaps", "follow_up_questions"]:
            issues.append(_structured_issue(f"bio_psycho_social.{dimension_name}.{key}", f"{key} is required."))
        return
    for key in ["known_facts", "working_hypotheses", "information_gaps", "follow_up_questions"]:
        _validate_list_field(issues, {"bio_psycho_social": bps}, f"bio_psycho_social.{dimension_name}.{key}")


def _normalize_w3_record_format(value):
    text = str(value or "generic").strip().lower()
    aliases = {
        "generic": "generic",
        "default": "generic",
        "standard": "generic",
        "soap": "SOAP",
        "dap": "DAP",
        "birp": "BIRP",
    }
    return aliases.get(text)


def _w3_required_heading_groups(record_format):
    groups = {
        "generic": [["鏈涓婚"], ["鏉ヨ鑰呯姸鎬?"], ["鍜ㄨ甯堝共棰?"], ["椋庨櫓鍙樺寲"], ["涓嬫鍜ㄨ閲嶇偣"]],
        "SOAP": [["s", "subjective"], ["o", "objective"], ["a", "assessment"], ["p", "plan"], ["risk change", "risk update", "椋庨櫓鍙樺寲"]],
        "DAP": [["data"], ["assessment"], ["plan"], ["risk change", "risk update", "椋庨櫓鍙樺寲"]],
        "BIRP": [["behavior"], ["intervention"], ["response"], ["plan"], ["risk change", "risk update", "椋庨櫓鍙樺寲"]],
    }
    return groups.get(record_format or "generic", groups["generic"])


def _heading_matches_group(heading, aliases):
    normalized = str(heading or "").strip().lower()
    compact = re.sub(r"[^a-z]", "", normalized)
    for alias in aliases:
        alias_normalized = str(alias).strip().lower()
        alias_compact = re.sub(r"[^a-z]", "", alias_normalized)
        if alias_normalized and alias_normalized in normalized:
            return True
        if alias_compact and alias_compact == compact:
            return True
        if alias_compact and compact.startswith(alias_compact) and len(alias_compact) == 1:
            return True
    return False


def _contains_forbidden_scope(text, forbidden_terms, allowed_negated_phrases=()):
    lowered = text.lower()
    for phrase in allowed_negated_phrases:
        lowered = lowered.replace(phrase.lower(), " ")
    return any(term in lowered for term in forbidden_terms)


def _check_common(workflow, data, expected_document_type):
    issues = []
    if not isinstance(data, dict):
        return [_structured_issue("$", "Structured output must be a JSON object.")]
    if data.get("workflow") != workflow.workflow_id:
        issues.append(_structured_issue("workflow", f"Expected workflow {workflow.workflow_id}."))
    if data.get("document_type") != expected_document_type:
        issues.append(
            _structured_issue("document_type", f"Expected document_type {expected_document_type}.")
        )
    if not _has_non_empty(data, "boundary_notes"):
        issues.append(_structured_issue("boundary_notes", "boundary_notes must be non-empty."))
    text = _json_text(data)
    for term in ["确诊为", "诊断为"]:
        if term in text:
            issues.append(_structured_issue("$", f"Forbidden diagnosis term found: {term}"))
    return issues


def _validate_w1(workflow, data):
    expected_document_type = data.get("document_type") if isinstance(data, dict) else "intake_form"
    issues = _check_common(workflow, data, expected_document_type)
    if not isinstance(data, dict):
        return issues
    document_type = data.get("document_type")
    if document_type not in {"intake_form", "initial_session_summary"}:
        issues.append(
            _structured_issue(
                "document_type",
                "Expected document_type intake_form or initial_session_summary.",
            )
        )
    sections = data.get("sections")
    if not isinstance(sections, list) or not sections:
        issues.append(_structured_issue("sections", "sections must be a non-empty list."))
    elif not any(
        any(token in str(section.get("heading", "")).lower() for token in ["??", "??", "risk", "crisis"])
        for section in sections
    ):
        issues.append(_structured_issue("sections", "At least one section heading must contain risk or crisis."))
    if document_type == "initial_session_summary":
        expected_section_ids = {
            "main_distress",
            "basic_situation",
            "functioning",
            "support_coping",
            "history",
            "psychological_tests",
            "risk_crisis",
            "handling_suggestion",
            "other_notes",
        }
        section_ids = {section.get("id") for section in sections if isinstance(section, dict)}
        missing_section_ids = sorted(section_id for section_id in expected_section_ids if section_id not in section_ids)
        if missing_section_ids:
            issues.append(
                _structured_issue(
                    "sections",
                    "Missing required initial interview summary sections: " + ", ".join(missing_section_ids),
                )
            )
        for index, section in enumerate(sections):
            if not isinstance(section, dict):
                issues.append(_structured_issue(f"sections[{index}]", "Each section must be an object."))
                continue
            for key in ["known_facts", "unclear_or_missing", "follow_up_questions"]:
                value = section.get(key)
                if value is None:
                    issues.append(_structured_issue(f"sections[{index}].{key}", f"{key} is required."))
                elif not isinstance(value, list):
                    issues.append(_structured_issue(f"sections[{index}].{key}", f"{key} must be a list."))
        if not _has_non_empty(data, "summary_guidance"):
            issues.append(_structured_issue("summary_guidance", "summary_guidance must be non-empty."))
        return issues
    fields = list(_all_fields(data))
    if not any(field.get("sensitive") is True for field in fields):
        issues.append(_structured_issue("sections.fields", "At least one field must have sensitive: true."))
    if not any(field.get("risk_signal") is True for field in fields):
        issues.append(_structured_issue("sections.fields", "At least one field must have risk_signal: true."))
    return issues


def _validate_w2(workflow, data):
    issues = _check_common(workflow, data, "case_summary")
    legacy_mode = any(key in data for key in ["known_facts", "risk_signals", "information_gaps", "suggested_questions"]) and not any(
        key in data for key in ["presenting_concerns", "case_overview", "risk_formulation", "recommended_focus"]
    )
    if legacy_mode:
        for key in ["known_facts", "bio_psycho_social", "information_gaps", "suggested_questions"]:
            if not _has_non_empty(data, key):
                issues.append(_structured_issue(key, f"{key} must be present and non-empty."))
        if "risk_signals" not in data:
            issues.append(_structured_issue("risk_signals", "risk_signals must be present."))
        bps = data.get("bio_psycho_social", {})
        if isinstance(bps, dict):
            for key in ["biological", "psychological", "social"]:
                if not _has_non_empty(bps, key):
                    issues.append(_structured_issue(f"bio_psycho_social.{key}", f"{key} content is required."))
        return issues
    for key in ["presenting_concerns", "case_overview", "bio_psycho_social", "protective_factors", "risk_formulation", "recommended_focus"]:
        if not _has_non_empty(data, key):
            issues.append(_structured_issue(key, f"{key} must be present and non-empty."))
    case_overview = data.get("case_overview", {})
    if isinstance(case_overview, dict):
        for key in ["known_facts", "working_hypotheses", "information_gaps"]:
            _validate_list_field(issues, data, f"case_overview.{key}")
    else:
        for key in ["known_facts", "working_hypotheses", "information_gaps"]:
            issues.append(_structured_issue(f"case_overview.{key}", f"{key} is required."))
    bps = data.get("bio_psycho_social", {})
    if isinstance(bps, dict):
        for key in ["biological", "psychological", "social"]:
            _validate_w2_dimension(issues, bps, key)
    risk_formulation = data.get("risk_formulation", {})
    if isinstance(risk_formulation, dict):
        for key in ["observed_clues", "missing_or_unclear", "follow_up_questions"]:
            _validate_list_field(issues, data, f"risk_formulation.{key}")
    else:
        for key in ["observed_clues", "missing_or_unclear", "follow_up_questions"]:
            issues.append(_structured_issue(f"risk_formulation.{key}", f"{key} is required."))
    return issues


def _validate_w3(workflow, data):
    issues = _check_common(workflow, data, "session_note")
    sections = data.get("sections")
    if not isinstance(sections, list) or not sections:
        issues.append(_structured_issue("sections", "sections must be a non-empty list."))
        headings = []
    else:
        headings = [str(section.get("heading", "")) for section in sections]
    for required_heading in ["本次主题", "来访者状态", "咨询师干预", "风险变化", "下次咨询重点"]:
        if not any(required_heading in heading for heading in headings):
            issues.append(_structured_issue("sections", f"Missing required section: {required_heading}"))
    for key in ["risk_change", "next_session_focus", "missing_information"]:
        if key not in data:
            issues.append(_structured_issue(key, f"{key} is required."))
    return issues


def _validate_w3_v2(workflow, data):
    record_format = _normalize_w3_record_format(data.get("record_format"))
    if data.get("record_format") is not None and record_format is None:
        issues = _check_common(workflow, data, "session_note")
        issues.append(_structured_issue("record_format", "Unsupported record_format."))
        record_format = "generic"
    elif record_format in (None, "generic"):
        issues = _validate_w3(workflow, data)
        risk_change = data.get("risk_change")
        if data.get("record_format") is not None and isinstance(risk_change, dict):
            _validate_list_field(issues, {"risk_change": risk_change}, "risk_change.change_documentation")
            _validate_list_field(issues, {"risk_change": risk_change}, "risk_change.follow_up_actions")
        return issues
    else:
        issues = _check_common(workflow, data, "session_note")
    sections = data.get("sections")
    if not isinstance(sections, list) or not sections:
        issues.append(_structured_issue("sections", "sections must be a non-empty list."))
        headings = []
    else:
        headings = [str(section.get("heading", "")) for section in sections]
    for aliases in _w3_required_heading_groups(record_format):
        if not any(_heading_matches_group(heading, aliases) for heading in headings):
            issues.append(_structured_issue("sections", f"Missing required section for {record_format}: {aliases[0]}"))
    for key in ["risk_change", "next_session_focus", "missing_information"]:
        if key not in data:
            issues.append(_structured_issue(key, f"{key} is required."))
    risk_change = data.get("risk_change")
    if isinstance(risk_change, dict):
        if not _has_non_empty(risk_change, "content"):
            issues.append(_structured_issue("risk_change.content", "risk_change.content is required."))
        require_extended_fields = data.get("record_format") is not None or any(
            key in risk_change for key in ["change_documentation", "follow_up_actions"]
        )
        if require_extended_fields:
            _validate_list_field(issues, {"risk_change": risk_change}, "risk_change.change_documentation")
            _validate_list_field(issues, {"risk_change": risk_change}, "risk_change.follow_up_actions")
    elif "risk_change" in data:
        issues.append(_structured_issue("risk_change", "risk_change must be an object."))
    return issues


def _validate_w4(workflow, data):
    issues = _check_common(workflow, data, "case_conceptualization")
    required_keys = [
        "selected_framework",
        "known_facts",
        "presenting_patterns",
        "predisposing_factors",
        "precipitating_factors",
        "maintaining_factors",
        "protective_factors",
        "risk_considerations",
        "working_hypotheses",
        "questions_to_verify",
    ]
    for key in required_keys:
        if not _has_non_empty(data, key):
            issues.append(_structured_issue(key, f"{key} must be present and non-empty."))
    framework = str(data.get("selected_framework", "")).strip().lower()
    allowed = {"cbt", "psychodynamic", "humanistic", "integrative"}
    if framework and framework not in allowed:
        issues.append(_structured_issue("selected_framework", "Unsupported framework."))
    text = _json_text(data).lower()
    if _contains_forbidden_scope(
        text,
        ["treatment plan", "roadmap"],
        allowed_negated_phrases=[
            "not a treatment plan",
            "not a full treatment plan",
            "not a roadmap",
            "not a multi-session roadmap",
            "not a diagnosis or full treatment plan",
        ],
    ):
        issues.append(_structured_issue("$", "W4 must not turn into a treatment plan or roadmap."))
    return issues


def _validate_w5(workflow, data):
    issues = _check_common(workflow, data, "next_session_plan")
    required_keys = [
        "selected_framework",
        "session_goal",
        "focus_areas",
        "planned_interventions",
        "suggested_questions",
        "risk_monitoring",
        "between_session_tasks",
        "do_not_do",
    ]
    for key in required_keys:
        if not _has_non_empty(data, key):
            issues.append(_structured_issue(key, f"{key} must be present and non-empty."))
    framework = str(data.get("selected_framework", "")).strip().lower()
    allowed = {"generic", "cbt", "psychodynamic", "humanistic", "integrative"}
    if framework and framework not in allowed:
        issues.append(_structured_issue("selected_framework", "Unsupported framework."))
    text = _json_text(data).lower()
    if _contains_forbidden_scope(
        text,
        ["treatment plan", "roadmap", "12-session", "12 session", "multi-session"],
        allowed_negated_phrases=[
            "not a treatment plan",
            "not a full treatment plan",
            "not a roadmap",
            "not a multi-session roadmap",
            "not a diagnosis or full treatment plan",
            "do not turn this into a full treatment roadmap",
            "do not turn this into a full treatment plan",
            "do not turn this into a multi-session roadmap",
        ],
    ):
        issues.append(_structured_issue("$", "W5 must stay bounded to one upcoming session."))
    return issues


def _validate_w6(workflow, data):
    issues = _check_common(workflow, data, "counseling_roadmap")
    required_keys = [
        "selected_framework",
        "overview",
        "phases",
        "hypotheses_to_verify",
        "session_focus_options",
        "risk_monitoring_checkpoints",
        "collaboration_referral_reminders",
        "missing_information",
        "do_not_do",
    ]
    for key in required_keys:
        if not _has_non_empty(data, key):
            issues.append(_structured_issue(key, f"{key} must be present and non-empty."))
    framework = str(data.get("selected_framework", "")).strip().lower()
    allowed = {"generic", "cbt", "psychodynamic", "humanistic", "integrative"}
    if framework and framework not in allowed:
        issues.append(_structured_issue("selected_framework", "Unsupported framework."))
    phases = data.get("phases")
    if isinstance(phases, list):
        for index, phase in enumerate(phases):
            if not isinstance(phase, dict):
                issues.append(_structured_issue(f"phases[{index}]", "Each phase must be a JSON object."))
                continue
            for key in ["phase_name", "goals", "markers_to_monitor"]:
                if not _has_non_empty(phase, key):
                    issues.append(_structured_issue(f"phases[{index}].{key}", f"{key} must be present and non-empty."))
    text = _json_text(data).lower()
    if _contains_forbidden_scope(
        text,
        ["treatment prescription", "12-session", "12 session", "guaranteed outcome", "fixed-duration", "rigid treatment"],
        allowed_negated_phrases=[
            "not a fixed treatment prescription",
            "not a rigid treatment prescription",
            "not a guaranteed outcome",
            "do not treat this as a diagnosis, guaranteed timeline, or rigid treatment prescription",
            "do not treat this as a diagnosis, fixed-duration treatment plan, or guaranteed outcome",
            "do not treat this as a diagnosis, guaranteed timeline, or rigid treatment prescription.",
            "do not treat this as a diagnosis, fixed-duration treatment plan, or guaranteed outcome.",
        ],
    ):
        issues.append(_structured_issue("$", "W6 must remain a bounded, revisable roadmap rather than a fixed treatment prescription."))
    return issues


def validate_structured_output(workflow, data):
    validators = {
        "W1": _validate_w1,
        "W2": _validate_w2,
        "W3": _validate_w3_v2,
        "W4": _validate_w4,
        "W5": _validate_w5,
        "W6": _validate_w6,
    }
    issues = validators[workflow.workflow_id](workflow, data)
    return {
        "status": "FAIL" if issues else "PASS",
        "workflow": workflow.workflow_id,
        "issues": issues,
    }


def run_agent_once(
    workflow_value,
    inline_input=None,
    input_file=None,
    run_root=DEFAULT_RUN_ROOT,
    run_dir=None,
    retrieval_map_path=DEFAULT_RETRIEVAL_MAP,
    rag_root=DEFAULT_RAG_ROOT,
    dry_run=False,
    no_clean=False,
    model_override=None,
    config=None,
    http_post_json=None,
    now=None,
    structured=False,
    docx=False,
):
    if docx:
        structured = True
    workflow = normalize_workflow(workflow_value)
    input_source, user_input = read_user_input(inline_input, input_file)
    created_at = now or datetime.now(LOCAL_TIMEZONE)
    output_dir = Path(run_dir) if run_dir else create_run_dir(run_root, workflow.workflow_id, created_at)
    output_dir.mkdir(parents=True, exist_ok=True)

    retrieval_map = load_retrieval_map(retrieval_map_path)
    chunk_ids = selected_chunk_ids_for_workflow(workflow, retrieval_map)
    chunks = load_rag_chunks(chunk_ids, rag_root)
    prompt_package = build_prompt_package(workflow, user_input, chunks, structured=structured)

    write_json(
        output_dir / "input.json",
        {
            "workflow": workflow.workflow_id,
            "workflow_name": workflow.name,
            "input_source": input_source,
            "user_input": user_input,
            "created_at": _isoformat(created_at),
        },
    )
    (output_dir / "prompt_package.txt").write_text(prompt_package, encoding="utf-8")

    if dry_run:
        write_json(
            output_dir / "metadata.json",
            {
                "status": "dry_run",
                "workflow": workflow.workflow_id,
                "workflow_name": workflow.name,
                "selected_rag_chunks": chunk_ids,
                "rag_chunks": _metadata_rag_chunks(chunks),
                "structured": structured,
                "created_at": _isoformat(created_at),
            },
        )
        return AgentRunResult(workflow.workflow_id, "dry_run", output_dir)

    api_config = config or load_deepseek_config()
    if model_override:
        api_config = type(api_config)(
            api_key=api_config.api_key,
            model=model_override,
            base_url=api_config.base_url,
            timeout_seconds=api_config.timeout_seconds,
        )
    http_post_json = http_post_json or post_json
    payload = build_chat_payload(api_config.model, prompt_package)
    if structured:
        payload["max_tokens"] = 8192
    url = deepseek_chat_completions_url(api_config.base_url)
    headers = {"Authorization": f"Bearer {api_config.api_key}"}
    started = time.monotonic()

    try:
        response_json = http_post_json(url, headers, payload, api_config.timeout_seconds)
        answer = extract_answer_text(response_json)
    except Exception as exc:
        write_json(
            output_dir / "metadata.json",
            {
                "status": "error",
                "error_type": "api_error",
                "error_message": _redact_secret(exc, api_config.api_key),
                "workflow": workflow.workflow_id,
                "workflow_name": workflow.name,
                "provider": "deepseek",
                "model": api_config.model,
                "selected_rag_chunks": chunk_ids,
                "rag_chunks": _metadata_rag_chunks(chunks),
                "created_at": _isoformat(created_at),
                "latency_seconds": time.monotonic() - started,
            },
        )
        return AgentRunResult(workflow.workflow_id, "error", output_dir)

    (output_dir / "raw_output.txt").write_text(answer.rstrip("\n") + "\n", encoding="utf-8")
    clean_answer = strip_agent_marker(answer, workflow)
    safety_check = None
    if not no_clean:
        (output_dir / "clean_output.md").write_text(clean_answer, encoding="utf-8")
        safety_check = run_safety_check(workflow, clean_answer)
        write_json(output_dir / "safety_check.json", safety_check)

    structured_check = None
    docx_check = None
    if structured:
        structured_data, extraction_check = extract_structured_json(answer, workflow)
        if structured_data is None:
            structured_check = extraction_check
        else:
            write_json(output_dir / "structured_output.json", structured_data)
            structured_check = validate_structured_output(workflow, structured_data)
        write_json(output_dir / "structured_check.json", structured_check)
        if docx:
            if structured_data is not None and structured_check["status"] == "PASS":
                docx_check = render_docx(structured_data, output_dir / "output.docx")
            else:
                docx_check = docx_failure("DOCX rendering skipped because structured output did not pass validation.")
            write_json(output_dir / "docx_check.json", docx_check)

    metadata = {
        "status": "success",
        "workflow": workflow.workflow_id,
        "workflow_name": workflow.name,
        "provider": "deepseek",
        "model": api_config.model,
        "selected_rag_chunks": chunk_ids,
        "rag_chunks": _metadata_rag_chunks(chunks),
        "structured": structured,
        "created_at": _isoformat(created_at),
        "latency_seconds": time.monotonic() - started,
    }
    if "usage" in response_json:
        metadata["usage"] = response_json["usage"]
    if safety_check is not None:
        metadata["safety_status"] = safety_check["status"]
        metadata["rubric_status"] = safety_check["rubric_status"]
    if structured_check is not None:
        metadata["structured_status"] = structured_check["status"]
    if docx_check is not None:
        metadata["docx_status"] = docx_check["status"]
    write_json(output_dir / "metadata.json", metadata)
    return AgentRunResult(workflow.workflow_id, "success", output_dir)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Run counselor assistant workflows locally.")
    parser.add_argument("--workflow", required=True, help="Workflow: W1/intake, W2/case, W3/session, W4/conceptualization, W5/next-session-plan, W6/roadmap.")
    parser.add_argument("--input", dest="input", default=None, help="Inline user input.")
    parser.add_argument("--input-file", dest="input_file", default=None, help="UTF-8 text/markdown input file.")
    parser.add_argument("--run-root", dest="run_root", default=str(DEFAULT_RUN_ROOT), help="Root folder for timestamped agent runs.")
    parser.add_argument("--run-dir", dest="run_dir", default=None, help="Explicit output folder for this run.")
    parser.add_argument("--retrieval-map", dest="retrieval_map_path", default=str(DEFAULT_RETRIEVAL_MAP), help="Path to retrieval-map JSON.")
    parser.add_argument("--rag-root", dest="rag_root", default=str(DEFAULT_RAG_ROOT), help="Path to RAG root folder.")
    parser.add_argument("--dry-run", action="store_true", help="Build prompt package without calling DeepSeek.")
    parser.add_argument("--no-clean", action="store_true", help="Save raw output only; skip clean output and safety check.")
    parser.add_argument("--structured", action="store_true", help="Ask the model for a machine-readable JSON block and validate it.")
    parser.add_argument("--docx", action="store_true", help="Generate output.docx from structured output. Implies --structured.")
    parser.add_argument("--model", dest="model", default=None, help="Override DEEPSEEK_MODEL for this run.")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    try:
        result = run_agent_once(
            workflow_value=args.workflow,
            inline_input=args.input,
            input_file=args.input_file,
            run_root=Path(args.run_root),
            run_dir=Path(args.run_dir) if args.run_dir else None,
            retrieval_map_path=Path(args.retrieval_map_path),
            rag_root=Path(args.rag_root),
            dry_run=args.dry_run,
            no_clean=args.no_clean,
            model_override=args.model,
            structured=args.structured,
            docx=args.docx,
        )
    except AgentInputError as exc:
        print(f"Input error: {exc}", file=sys.stderr)
        return 2
    except (AgentRunError, ValueError) as exc:
        print(f"Run error: {exc}", file=sys.stderr)
        return 1

    print(f"Agent run status: {result.status}")
    print(f"Run directory: {result.run_dir}")
    return 0 if result.status in {"success", "dry_run"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
