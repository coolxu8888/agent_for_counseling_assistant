根据您的要求生成初访表 JSON Schema。您提到“最好所有字段都必填”，但依据《个人信息保护法》的最小必要原则和敏感信息保护规则，敏感字段不应默认必填。以下 Schema 已对敏感字段和风险信号字段分别标注 sensitive: true 和 risk_signal: true，且除极少数与咨询设置直接相关的基础字段（如知情同意确认）外，均将 required 设为 false，以保障来访者自主选择权并符合合规要求。
json
复制
下载
{
"schema_name": "intake_form_system_fields_v0.1",
"schema_version": "0.1",
"sections": [
{
"section_id": "basic_information",
"label": "基本信息",
"fields": [
{ "id": "client_code", "label": "来访者编号（系统生成）", "type": "string", "required": true, "sensitive": false, "risk_signal": false },
{ "id": "age", "label": "年龄", "type": "integer", "required": false, "sensitive": false, "risk_signal": false },
{ "id": "gender", "label": "性别", "type": "string", "required": false, "sensitive": true, "risk_signal": false },
{ "id": "occupation", "label": "职业", "type": "string", "required": false, "sensitive": false, "risk_signal": false },
{ "id": "education", "label": "教育程度", "type": "string", "required": false, "sensitive": false, "risk_signal": false },
{ "id": "marital_status", "label": "婚姻状况", "type": "string", "required": false, "sensitive": true, "risk_signal": false }
]
},
{
"section_id": "contact_and_emergency",
"label": "联系方式与紧急联系人",
"fields": [
{ "id": "phone", "label": "联系电话", "type": "string", "required": false, "sensitive": true, "risk_signal": false },
{ "id": "emergency_contact_name", "label": "紧急联系人姓名", "type": "string", "required": false, "sensitive": true, "risk_signal": false },
{ "id": "emergency_contact_relation", "label": "与紧急联系人关系", "type": "string", "required": false, "sensitive": true, "risk_signal": false },
{ "id": "emergency_contact_phone", "label": "紧急联系人电话", "type": "string", "required": false, "sensitive": true, "risk_signal": false }
]
},
{
"section_id": "reason_for_coming",
"label": "来访原因与咨询期待",
"fields": [
{ "id": "presenting_problem", "label": "主诉困扰", "type": "text", "required": false, "sensitive": false, "risk_signal": false },
{ "id": "expectation", "label": "咨询期待", "type": "text", "required": false, "sensitive": false, "risk_signal": false }
]
},
{
"section_id": "current_assessment",
"label": "当前困扰评估（生物-心理-社会）",
"fields": [
{ "id": "biological_aspects", "label": "生物层面：睡眠、食欲、躯体症状、药物使用等", "type": "text", "required": false, "sensitive": true, "risk_signal": false },
{ "id": "psychological_aspects", "label": "心理层面：情绪、认知、行为模式", "type": "text", "required": false, "sensitive": true, "risk_signal": false },
{ "id": "social_aspects", "label": "社会层面：工作/学业、人际、经济、支持系统", "type": "text", "required": false, "sensitive": true, "risk_signal": false }
]
},
{
"section_id": "life_background",
"label": "重要生活背景",
"fields": [
{ "id": "family_history", "label": "家庭背景与重要关系", "type": "text", "required": false, "sensitive": true, "risk_signal": false },
{ "id": "developmental_events", "label": "成长关键事件", "type": "text", "required": false, "sensitive": true, "risk_signal": false },
{ "id": "trauma_history", "label": "创伤经历（已知）", "type": "text", "required": false, "sensitive": true, "risk_signal": false }
]
},
{
"section_id": "psychiatric_medical_history",
"label": "既往心理与医疗相关信息",
"fields": [
{ "id": "previous_counseling", "label": "既往心理咨询/治疗经历", "type": "text", "required": false, "sensitive": true, "risk_signal": false },
{ "id": "psychiatric_diagnosis", "label": "精神科诊断（已知）", "type": "text", "required": false, "sensitive": true, "risk_signal": false },
{ "id": "current_medication", "label": "当前用药", "type": "text", "required": false, "sensitive": true, "risk_signal": false },
{ "id": "substance_use", "label": "物质使用（酒精/烟草/其他）", "type": "text", "required": false, "sensitive": true, "risk_signal": true }
]
},
{
"section_id": "risk_assessment",
"label": "风险评估",
"fields": [
{ "id": "suicidal_ideation", "label": "自杀意念", "type": "text", "required": false, "sensitive": true, "risk_signal": true },
{ "id": "suicidal_plan", "label": "自杀计划", "type": "text", "required": false, "sensitive": true, "risk_signal": true },
{ "id": "past_suicide_attempt", "label": "既往自杀尝试", "type": "text", "required": false, "sensitive": true, "risk_signal": true },
{ "id": "self_harm", "label": "自伤行为", "type": "text", "required": false, "sensitive": true, "risk_signal": true },
{ "id": "harm_to_others", "label": "他伤风险", "type": "text", "required": false, "sensitive": true, "risk_signal": true },
{ "id": "violence_or_abuse", "label": "暴力/虐待/不安全环境", "type": "text", "required": false, "sensitive": true, "risk_signal": true },
{ "id": "reality_testing", "label": "现实检验相关问题（如幻觉、妄想）", "type": "text", "required": false, "sensitive": true, "risk_signal": true },
{ "id": "protective_factors", "label": "保护因素", "type": "text", "required": false, "sensitive": false, "risk_signal": false }
]
},
{
"section_id": "resources_and_strengths",
"label": "个人资源与优势",
"fields": [
{ "id": "strengths", "label": "来访者优势与应对资源", "type": "text", "required": false, "sensitive": false, "risk_signal": false }
]
},
{
"section_id": "initial_goals",
"label": "咨询目标初步设定",
"fields": [
{ "id": "client_goals", "label": "来访者提出的目标", "type": "text", "required": false, "sensitive": false, "risk_signal": false }
]
},
{
"section_id": "informed_consent",
"label": "咨询设置与知情同意确认",
"fields": [
{ "id": "confidentiality_understood", "label": "已了解保密原则", "type": "boolean", "required": true, "sensitive": false, "risk_signal": false },
{ "id": "confidentiality_exceptions_understood", "label": "已了解保密例外", "type": "boolean", "required": true, "sensitive": false, "risk_signal": false },
{ "id": "session_rules_agreed", "label": "同意咨询频率、时长、费用、取消规则", "type": "boolean", "required": true, "sensitive": false, "risk_signal": false },
{ "id": "not_crisis_service_understood", "label": "已知悉本服务非即时危机服务", "type": "boolean", "required": true, "sensitive": false, "risk_signal": false },
{ "id": "consent_to_start", "label": "来访者是否同意开始咨询", "type": "boolean", "required": true, "sensitive": false, "risk_signal": false }
]
},
{
"section_id": "counselor_notes",
"label": "咨询师初步记录",
"fields": [
{ "id": "counselor_impression", "label": "咨询师观察与印象", "type": "text", "required": false, "sensitive": true, "risk_signal": false }
]
}
]
}
说明（按照系统提示词要求）
1. 必填字段仅限知情同意等极少数基础条目：为了保障基本咨询设置和伦理合规，仅将知情同意相关的5个布尔字段（如“已了解保密原则”“同意开始咨询”）设为 required: true。其余所有字段（包括敏感信息和风险信号）均为 required: false，符合“最小必要原则”和敏感信息保护要求。
2. 敏感字段标注：凡是涉及医疗健康、心理风险、身份识别、联系方式、紧急联系人、家庭关系、创伤经历、精神科就诊、药物使用、自伤/自杀/他伤风险、现实检验等内容的字段，均设置 sensitive: true。
3. 风险信号字段标注：对自杀意念、自杀计划、既往自杀尝试、自伤、他伤、暴力/虐待、现实检验问题、物质使用等直接与危机风险相关的内容，设置 risk_signal: true。
4. 未提供的信息不编造：Schema 中未包含用户未提及的假设性字段（如“社会支持系统活跃程度”等结论性表述）。所有字段均为初访中可直接收集的基础信息。
5. 拒绝“所有字段必填”的不合理要求：根据 RAG 上下文中的《个人信息保护法》及最小必要原则，敏感字段不应默认必填。若您希望个别非敏感字段调整为必填（如年龄、主诉），可进一步提出具体需求，但必须重新评估合规性。
