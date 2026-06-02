# 咨询师端辅助 Agent MVP

## MVP 名称

初访信息收集表生成能力

## MVP 目标

当咨询师输入“给我一个初访信息收集表”时，Agent 能生成一套可用于初访前后工作的结构化表单，帮助咨询师系统了解来访者的基本信息、咨询目的、个人需求、当前困扰、风险状况、资源支持与初步咨询目标。

本 MVP 拆分为三个版本：

1. 咨询师访谈版：适合咨询师在初访过程中边问边记录。
2. 来访者预填写版：适合来访者在咨询前自行填写。
3. 系统结构化字段版：适合产品落库、后续 RAG、报告生成与自动化处理。

## 使用边界

- 本表单用于咨询前信息收集与初步评估辅助。
- Agent 不直接作出诊断，不替代咨询师专业判断。
- 涉及自伤、自杀、他伤、虐待、精神病性症状等高风险信息时，应提示咨询师进行进一步风险评估，并按机构危机流程处理。
- 所有来访者信息都应按照隐私保护、知情同意和数据最小化原则处理。

---

# 版本一：咨询师访谈版

## 适用场景

咨询师在初访会谈中使用。问题较完整，适合边访谈边记录，也适合用于初访后整理。

## 一、基本信息

| 项目 | 记录 |
|---|---|
| 来访者姓名 |  |
| 性别 / 性别认同 |  |
| 年龄 |  |
| 出生日期 |  |
| 联系方式 |  |
| 紧急联系人及关系 |  |
| 紧急联系人电话 |  |
| 婚恋状态 |  |
| 职业 / 年级 |  |
| 最高学历 |  |
| 居住情况 |  |
| 主要经济来源 |  |
| 推荐 / 转介来源 |  |
| 是否曾接受心理咨询或精神科治疗 |  |
| 是否正在服药 |  |
| 是否有重大身体疾病史 |  |

## 二、来访原因与咨询期待

| 访谈问题 | 记录 |
|---|---|
| 你这次来咨询，最主要想谈的问题是什么？ |  |
| 这个问题大概从什么时候开始出现？ |  |
| 最近是否有明显加重或缓解？ |  |
| 是什么让你决定现在寻求咨询？ |  |
| 你希望通过咨询获得什么帮助？ |  |
| 如果咨询是有效的，你希望自己发生哪些变化？ |  |
| 目前最想优先解决的一个问题是什么？ |  |
| 你对咨询师或咨询过程有什么期待？ |  |
| 你有什么担心或顾虑吗？ |  |

## 三、当前困扰评估

| 维度 | 访谈问题 | 记录 |
|---|---|---|
| 情绪状态 | 最近主要的情绪是什么？例如焦虑、低落、愤怒、空虚、麻木等。 |  |
| 情绪强度 | 如果 0 到 10 分表示痛苦程度，你现在大概是几分？ |  |
| 持续时间 | 这种状态通常会持续多久？一天中什么时候最明显？ |  |
| 触发因素 | 通常什么事情会让这种状态变严重？ |  |
| 应对方式 | 当这些感受出现时，你通常会怎么处理？ |  |
| 睡眠 | 最近睡眠情况如何？入睡、早醒、多梦、睡眠质量如何？ |  |
| 食欲 | 最近食欲或体重是否有明显变化？ |  |
| 精力 | 最近精力、注意力、行动力如何？ |  |
| 工作 / 学习 | 当前困扰对工作、学习或生活功能有什么影响？ |  |
| 人际关系 | 当前困扰对亲密关系、家庭关系、朋友关系有什么影响？ |  |

## 四、重要生活背景

| 访谈问题 | 记录 |
|---|---|
| 目前与你同住的人有哪些？关系如何？ |  |
| 你成长过程中主要照顾者是谁？ |  |
| 你和父母 / 重要家人的关系如何？ |  |
| 近期是否经历重大生活事件？例如分手、离职、考试、搬家、亲人离世等。 |  |
| 过去是否经历过创伤、霸凌、暴力、重大丧失或长期压力？ |  |
| 目前生活中最大的压力来源是什么？ |  |
| 目前生活中有哪些支持你的人或资源？ |  |
| 你通常如何看待自己？ |  |
| 你通常如何理解自己和他人的关系？ |  |

## 五、既往心理与医疗相关信息

| 访谈问题 | 记录 |
|---|---|
| 过去是否接受过心理咨询？如果有，时间、频率、体验如何？ |  |
| 过去是否有精神科就诊经历？ |  |
| 是否曾被告知有心理或精神相关诊断？ |  |
| 是否正在或曾经服用精神科药物？药名、剂量、效果如何？ |  |
| 是否有住院、急诊或危机干预经历？ |  |
| 家族中是否有人有精神疾病、成瘾、自杀或重大心理困扰史？ |  |
| 是否有长期身体疾病、疼痛或重大手术经历？ |  |

## 六、风险评估

| 风险维度 | 访谈问题 | 记录 |
|---|---|---|
| 自伤风险 | 近期是否有伤害自己的想法或行为？ |  |
| 自杀意念 | 近期是否出现过“不想活了”“希望消失”“想结束生命”等想法？ |  |
| 自杀计划 | 如果有类似想法，是否想过具体方式、时间或地点？ |  |
| 自杀准备 | 是否做过准备行为？例如囤药、写遗书、交代事情等。 |  |
| 既往风险 | 过去是否有自伤、自杀尝试或高危冲动行为？ |  |
| 他伤风险 | 是否有想伤害他人的念头、计划或冲动？ |  |
| 暴力 / 虐待 | 目前是否处于被威胁、被控制、被虐待或不安全的环境中？ |  |
| 物质使用 | 是否存在酒精、药物或其他物质使用问题？ |  |
| 现实检验 | 最近是否有明显幻听、幻视、被害感、失控感或与现实脱节的体验？ |  |
| 保护因素 | 当你很痛苦时，是什么让你还能坚持下来的？ |  |
| 当前安全等级 | 低 / 中 / 高，依据是什么？ |  |

## 七、个人资源与优势

| 访谈问题 | 记录 |
|---|---|
| 你觉得自己有哪些力量、优点或曾经帮助你撑过困难的能力？ |  |
| 过去遇到困难时，哪些方式曾经有效？ |  |
| 目前谁是你可以信任或求助的人？ |  |
| 有没有让你感到稳定、放松或有意义的事情？ |  |
| 你希望咨询师更多了解你的哪些部分？ |  |

## 八、咨询目标初步设定

| 访谈问题 | 记录 |
|---|---|
| 你最希望优先改变的是什么？ |  |
| 这个目标对你为什么重要？ |  |
| 如果用具体行为描述，改变发生后你会做些什么不同的事？ |  |
| 你希望多长时间内看到一些变化？ |  |
| 你愿意为这个目标尝试哪些行动？ |  |
| 咨询师初步理解的咨询目标 |  |
| 来访者确认后的咨询目标 |  |

## 九、咨询设置与知情同意确认

| 项目 | 确认情况 |
|---|---|
| 已说明咨询保密原则 |  |
| 已说明保密例外情况，如自伤、自杀、他伤、虐待、法律要求等 |  |
| 已说明咨询频率、时长、费用、取消规则 |  |
| 已说明咨询并非即时危机服务 |  |
| 已说明记录保存与隐私保护方式 |  |
| 来访者是否同意开始咨询 |  |
| 其他需要说明的事项 |  |

## 十、咨询师初步记录

| 项目 | 记录 |
|---|---|
| 初访总体印象 |  |
| 主要问题摘要 |  |
| 可能的维持因素 |  |
| 初步个案概念化假设 |  |
| 初步风险判断 |  |
| 是否建议转介 / 联合精神科评估 |  |
| 下次访谈重点 |  |
| 咨询师备注 |  |

---

# 版本二：来访者预填写版

## 适用场景

来访者在咨询前自行填写。语言更温和，问题更简洁，避免过度专业化。该版本可帮助咨询师提前了解来访者情况，也能让初访更聚焦。

## 填写说明

这份表格用于帮助咨询师更好地了解你的情况。你可以只填写自己愿意填写的部分。如果某些问题让你感到不适，可以留空，并在咨询中再决定是否讨论。

## 一、基本信息

| 项目 | 填写内容 |
|---|---|
| 姓名或称呼 |  |
| 年龄 |  |
| 性别 / 性别认同 |  |
| 联系方式 |  |
| 紧急联系人及关系 |  |
| 紧急联系人电话 |  |
| 职业 / 年级 |  |
| 婚恋状态 |  |
| 目前和谁一起居住 |  |
| 是否曾接受心理咨询 | 是 / 否 / 不确定 |
| 是否曾看过精神科 | 是 / 否 / 不确定 |
| 是否正在服用精神科相关药物 | 是 / 否 / 不确定 |

## 二、这次想寻求的帮助

| 问题 | 填写内容 |
|---|---|
| 你这次最想谈的事情是什么？ |  |
| 这个困扰大概持续多久了？ |  |
| 最近发生了什么，让你觉得现在需要寻求帮助？ |  |
| 你希望咨询能帮你改善什么？ |  |
| 如果咨询有帮助，你希望自己有什么变化？ |  |
| 你对咨询有什么期待或担心？ |  |

## 三、最近的状态

| 问题 | 填写内容 |
|---|---|
| 最近最常出现的情绪是什么？ |  |
| 如果 0 到 10 分表示痛苦程度，你最近平均大概是几分？ |  |
| 最近睡眠情况怎么样？ |  |
| 最近食欲或体重有没有明显变化？ |  |
| 最近精力、注意力和行动力怎么样？ |  |
| 这些困扰对你的学习、工作或生活有什么影响？ |  |
| 这些困扰对你的人际关系有什么影响？ |  |
| 当你难受时，通常会怎么应对？ |  |

## 四、生活背景

| 问题 | 填写内容 |
|---|---|
| 目前生活中最大的压力来源是什么？ |  |
| 最近是否经历过重要事件或变化？ |  |
| 你和家人或重要他人的关系大致如何？ |  |
| 过去是否有一些经历至今仍对你有影响？如不想填写，可以留空。 |  |
| 目前有哪些人或事情能给你支持？ |  |

## 五、安全相关问题

| 问题 | 填写内容 |
|---|---|
| 最近是否有伤害自己的想法或行为？ | 是 / 否 / 不确定 |
| 最近是否有“不想活了”“希望消失”“想结束生命”等想法？ | 是 / 否 / 不确定 |
| 如果有类似想法，是否有具体计划或准备？ | 是 / 否 / 不适用 |
| 过去是否有过自伤或自杀尝试？ | 是 / 否 / 不确定 |
| 是否有想伤害他人的念头或冲动？ | 是 / 否 / 不确定 |
| 你目前是否处在让你感到不安全、被威胁或被控制的环境中？ | 是 / 否 / 不确定 |
| 最近是否明显依赖酒精、药物或其他物质来应对情绪？ | 是 / 否 / 不确定 |

## 六、你的资源与期待

| 问题 | 填写内容 |
|---|---|
| 你觉得自己有哪些力量或优点？ |  |
| 过去遇到困难时，哪些方法曾经对你有帮助？ |  |
| 目前谁是你比较信任或可以求助的人？ |  |
| 有哪些事情会让你感到稳定、放松或有意义？ |  |
| 你希望咨询师特别了解你的哪些部分？ |  |

## 七、咨询目标

| 问题 | 填写内容 |
|---|---|
| 你最希望优先改变的一件事是什么？ |  |
| 这个改变对你为什么重要？ |  |
| 如果改变发生了，你觉得生活中会出现哪些具体不同？ |  |
| 你愿意先尝试做哪些小行动？ |  |

## 八、知情同意确认

| 项目 | 确认 |
|---|---|
| 我了解心理咨询有保密原则 | 已了解 / 需进一步说明 |
| 我了解在涉及自伤、自杀、他伤、虐待或法律要求等情况下，咨询师可能需要采取保护性措施 | 已了解 / 需进一步说明 |
| 我了解心理咨询不是即时危机服务 | 已了解 / 需进一步说明 |
| 我同意咨询师在专业和隐私保护范围内使用这些信息帮助开展咨询 | 同意 / 暂不确定 |

---

# 版本三：系统结构化字段版

## 适用场景

用于产品落库、表单配置、后续报告生成、RAG 检索、风险评估和 Agent 工作流编排。

## JSON Schema 草案

```json
{
  "schema_name": "initial_intake_form",
  "schema_version": "0.1.0",
  "language": "zh-CN",
  "sections": [
    {
      "id": "basic_info",
      "title": "基本信息",
      "fields": [
        {
          "id": "client_name",
          "label": "来访者姓名或称呼",
          "type": "text",
          "required": false,
          "sensitive": true
        },
        {
          "id": "age",
          "label": "年龄",
          "type": "number",
          "required": false,
          "sensitive": true
        },
        {
          "id": "gender_identity",
          "label": "性别 / 性别认同",
          "type": "text",
          "required": false,
          "sensitive": true
        },
        {
          "id": "contact",
          "label": "联系方式",
          "type": "text",
          "required": false,
          "sensitive": true
        },
        {
          "id": "emergency_contact_name",
          "label": "紧急联系人及关系",
          "type": "text",
          "required": false,
          "sensitive": true
        },
        {
          "id": "emergency_contact_phone",
          "label": "紧急联系人电话",
          "type": "text",
          "required": false,
          "sensitive": true
        },
        {
          "id": "occupation_or_grade",
          "label": "职业 / 年级",
          "type": "text",
          "required": false,
          "sensitive": false
        },
        {
          "id": "relationship_status",
          "label": "婚恋状态",
          "type": "single_select",
          "options": ["单身", "恋爱中", "已婚", "离异", "丧偶", "其他", "不愿说明"],
          "required": false,
          "sensitive": false
        },
        {
          "id": "living_situation",
          "label": "居住情况",
          "type": "text",
          "required": false,
          "sensitive": false
        },
        {
          "id": "referral_source",
          "label": "推荐 / 转介来源",
          "type": "text",
          "required": false,
          "sensitive": false
        }
      ]
    },
    {
      "id": "presenting_concern",
      "title": "来访原因与咨询期待",
      "fields": [
        {
          "id": "main_concern",
          "label": "这次最主要想谈的问题是什么？",
          "type": "long_text",
          "required": true,
          "sensitive": true
        },
        {
          "id": "concern_onset",
          "label": "这个问题大概从什么时候开始出现？",
          "type": "text",
          "required": false,
          "sensitive": false
        },
        {
          "id": "recent_change",
          "label": "最近是否有明显加重或缓解？",
          "type": "long_text",
          "required": false,
          "sensitive": false
        },
        {
          "id": "help_seeking_trigger",
          "label": "是什么让你决定现在寻求咨询？",
          "type": "long_text",
          "required": false,
          "sensitive": true
        },
        {
          "id": "expectations",
          "label": "希望通过咨询获得什么帮助？",
          "type": "long_text",
          "required": false,
          "sensitive": true
        },
        {
          "id": "primary_priority",
          "label": "目前最想优先解决的问题是什么？",
          "type": "long_text",
          "required": false,
          "sensitive": true
        },
        {
          "id": "concerns_about_counseling",
          "label": "对咨询师或咨询过程有什么期待、担心或顾虑？",
          "type": "long_text",
          "required": false,
          "sensitive": true
        }
      ]
    },
    {
      "id": "current_functioning",
      "title": "当前困扰评估",
      "fields": [
        {
          "id": "current_emotions",
          "label": "最近主要的情绪状态",
          "type": "multi_select",
          "options": ["焦虑", "低落", "愤怒", "空虚", "麻木", "恐惧", "内疚", "羞耻", "其他"],
          "required": false,
          "sensitive": true
        },
        {
          "id": "distress_score",
          "label": "当前痛苦程度，0 到 10 分",
          "type": "scale",
          "min": 0,
          "max": 10,
          "required": false,
          "sensitive": true
        },
        {
          "id": "duration_pattern",
          "label": "情绪或困扰的持续时间与出现规律",
          "type": "long_text",
          "required": false,
          "sensitive": true
        },
        {
          "id": "triggers",
          "label": "常见触发因素",
          "type": "long_text",
          "required": false,
          "sensitive": true
        },
        {
          "id": "coping_methods",
          "label": "当前应对方式",
          "type": "long_text",
          "required": false,
          "sensitive": true
        },
        {
          "id": "sleep",
          "label": "睡眠情况",
          "type": "long_text",
          "required": false,
          "sensitive": true
        },
        {
          "id": "appetite_weight",
          "label": "食欲或体重变化",
          "type": "long_text",
          "required": false,
          "sensitive": true
        },
        {
          "id": "energy_attention",
          "label": "精力、注意力和行动力",
          "type": "long_text",
          "required": false,
          "sensitive": true
        },
        {
          "id": "work_study_impact",
          "label": "对工作或学习的影响",
          "type": "long_text",
          "required": false,
          "sensitive": true
        },
        {
          "id": "relationship_impact",
          "label": "对人际关系的影响",
          "type": "long_text",
          "required": false,
          "sensitive": true
        }
      ]
    },
    {
      "id": "life_context",
      "title": "重要生活背景",
      "fields": [
        {
          "id": "current_household",
          "label": "目前同住者及关系",
          "type": "long_text",
          "required": false,
          "sensitive": true
        },
        {
          "id": "family_relationships",
          "label": "家庭或重要关系情况",
          "type": "long_text",
          "required": false,
          "sensitive": true
        },
        {
          "id": "recent_life_events",
          "label": "近期重大生活事件",
          "type": "long_text",
          "required": false,
          "sensitive": true
        },
        {
          "id": "past_adversity_or_trauma",
          "label": "过去重要压力、创伤、霸凌、暴力或重大丧失经历",
          "type": "long_text",
          "required": false,
          "sensitive": true
        },
        {
          "id": "current_stressors",
          "label": "当前主要压力来源",
          "type": "long_text",
          "required": false,
          "sensitive": true
        },
        {
          "id": "support_resources",
          "label": "当前支持资源",
          "type": "long_text",
          "required": false,
          "sensitive": true
        }
      ]
    },
    {
      "id": "clinical_history",
      "title": "既往心理与医疗相关信息",
      "fields": [
        {
          "id": "previous_counseling",
          "label": "过去心理咨询经历",
          "type": "long_text",
          "required": false,
          "sensitive": true
        },
        {
          "id": "psychiatric_history",
          "label": "精神科就诊经历",
          "type": "long_text",
          "required": false,
          "sensitive": true
        },
        {
          "id": "diagnosis_history",
          "label": "既往被告知的心理或精神相关诊断",
          "type": "long_text",
          "required": false,
          "sensitive": true
        },
        {
          "id": "medication_history",
          "label": "精神科药物使用情况",
          "type": "long_text",
          "required": false,
          "sensitive": true
        },
        {
          "id": "hospitalization_or_crisis_history",
          "label": "住院、急诊或危机干预经历",
          "type": "long_text",
          "required": false,
          "sensitive": true
        },
        {
          "id": "family_mental_health_history",
          "label": "家族精神健康、成瘾、自杀或重大心理困扰史",
          "type": "long_text",
          "required": false,
          "sensitive": true
        },
        {
          "id": "medical_history",
          "label": "长期身体疾病、疼痛或重大手术经历",
          "type": "long_text",
          "required": false,
          "sensitive": true
        }
      ]
    },
    {
      "id": "risk_assessment",
      "title": "风险评估",
      "fields": [
        {
          "id": "self_harm_ideation",
          "label": "近期是否有伤害自己的想法或行为",
          "type": "single_select",
          "options": ["否", "是", "不确定", "未询问"],
          "required": false,
          "sensitive": true,
          "risk_signal": true
        },
        {
          "id": "suicidal_ideation",
          "label": "近期是否有不想活、希望消失或想结束生命的想法",
          "type": "single_select",
          "options": ["否", "是", "不确定", "未询问"],
          "required": false,
          "sensitive": true,
          "risk_signal": true
        },
        {
          "id": "suicide_plan",
          "label": "是否有具体自杀方式、时间、地点或计划",
          "type": "single_select",
          "options": ["否", "是", "不确定", "不适用", "未询问"],
          "required": false,
          "sensitive": true,
          "risk_signal": true
        },
        {
          "id": "suicide_preparation",
          "label": "是否有准备行为，如囤药、写遗书、交代事情等",
          "type": "single_select",
          "options": ["否", "是", "不确定", "不适用", "未询问"],
          "required": false,
          "sensitive": true,
          "risk_signal": true
        },
        {
          "id": "past_attempts",
          "label": "过去是否有自伤、自杀尝试或高危冲动行为",
          "type": "single_select",
          "options": ["否", "是", "不确定", "未询问"],
          "required": false,
          "sensitive": true,
          "risk_signal": true
        },
        {
          "id": "harm_to_others",
          "label": "是否有伤害他人的念头、计划或冲动",
          "type": "single_select",
          "options": ["否", "是", "不确定", "未询问"],
          "required": false,
          "sensitive": true,
          "risk_signal": true
        },
        {
          "id": "abuse_or_unsafe_environment",
          "label": "是否处于被威胁、被控制、被虐待或不安全环境中",
          "type": "single_select",
          "options": ["否", "是", "不确定", "未询问"],
          "required": false,
          "sensitive": true,
          "risk_signal": true
        },
        {
          "id": "substance_use_risk",
          "label": "是否存在酒精、药物或其他物质使用风险",
          "type": "single_select",
          "options": ["否", "是", "不确定", "未询问"],
          "required": false,
          "sensitive": true,
          "risk_signal": true
        },
        {
          "id": "reality_testing_concerns",
          "label": "是否存在幻听、幻视、被害感、失控感或与现实脱节体验",
          "type": "single_select",
          "options": ["否", "是", "不确定", "未询问"],
          "required": false,
          "sensitive": true,
          "risk_signal": true
        },
        {
          "id": "protective_factors",
          "label": "保护因素",
          "type": "long_text",
          "required": false,
          "sensitive": true
        },
        {
          "id": "risk_level",
          "label": "当前安全等级",
          "type": "single_select",
          "options": ["低", "中", "高", "待进一步评估"],
          "required": false,
          "sensitive": true
        },
        {
          "id": "risk_rationale",
          "label": "风险等级依据",
          "type": "long_text",
          "required": false,
          "sensitive": true
        }
      ]
    },
    {
      "id": "strengths_and_resources",
      "title": "个人资源与优势",
      "fields": [
        {
          "id": "strengths",
          "label": "个人力量、优点或曾经帮助其撑过困难的能力",
          "type": "long_text",
          "required": false,
          "sensitive": true
        },
        {
          "id": "effective_past_coping",
          "label": "过去有效的应对方式",
          "type": "long_text",
          "required": false,
          "sensitive": true
        },
        {
          "id": "trusted_people",
          "label": "可信任或可求助的人",
          "type": "long_text",
          "required": false,
          "sensitive": true
        },
        {
          "id": "stabilizing_activities",
          "label": "带来稳定、放松或意义感的事情",
          "type": "long_text",
          "required": false,
          "sensitive": true
        }
      ]
    },
    {
      "id": "goals",
      "title": "咨询目标初步设定",
      "fields": [
        {
          "id": "priority_goal",
          "label": "最希望优先改变的事情",
          "type": "long_text",
          "required": false,
          "sensitive": true
        },
        {
          "id": "goal_importance",
          "label": "该目标的重要性",
          "type": "long_text",
          "required": false,
          "sensitive": true
        },
        {
          "id": "behavioral_indicators",
          "label": "改变发生后的具体行为表现",
          "type": "long_text",
          "required": false,
          "sensitive": true
        },
        {
          "id": "expected_timeline",
          "label": "期望看到变化的时间范围",
          "type": "text",
          "required": false,
          "sensitive": false
        },
        {
          "id": "client_willing_actions",
          "label": "来访者愿意尝试的行动",
          "type": "long_text",
          "required": false,
          "sensitive": true
        },
        {
          "id": "counselor_initial_goal",
          "label": "咨询师初步理解的咨询目标",
          "type": "long_text",
          "required": false,
          "sensitive": true
        },
        {
          "id": "confirmed_goal",
          "label": "来访者确认后的咨询目标",
          "type": "long_text",
          "required": false,
          "sensitive": true
        }
      ]
    },
    {
      "id": "informed_consent",
      "title": "咨询设置与知情同意确认",
      "fields": [
        {
          "id": "confidentiality_explained",
          "label": "已说明咨询保密原则",
          "type": "boolean",
          "required": false,
          "sensitive": false
        },
        {
          "id": "limits_of_confidentiality_explained",
          "label": "已说明保密例外情况",
          "type": "boolean",
          "required": false,
          "sensitive": false
        },
        {
          "id": "session_policy_explained",
          "label": "已说明咨询频率、时长、费用、取消规则",
          "type": "boolean",
          "required": false,
          "sensitive": false
        },
        {
          "id": "not_crisis_service_explained",
          "label": "已说明咨询并非即时危机服务",
          "type": "boolean",
          "required": false,
          "sensitive": false
        },
        {
          "id": "privacy_storage_explained",
          "label": "已说明记录保存与隐私保护方式",
          "type": "boolean",
          "required": false,
          "sensitive": false
        },
        {
          "id": "client_consent",
          "label": "来访者是否同意开始咨询",
          "type": "single_select",
          "options": ["同意", "暂不确定", "不同意"],
          "required": false,
          "sensitive": false
        },
        {
          "id": "other_consent_notes",
          "label": "其他需要说明的事项",
          "type": "long_text",
          "required": false,
          "sensitive": true
        }
      ]
    },
    {
      "id": "counselor_notes",
      "title": "咨询师初步记录",
      "fields": [
        {
          "id": "initial_impression",
          "label": "初访总体印象",
          "type": "long_text",
          "required": false,
          "sensitive": true
        },
        {
          "id": "problem_summary",
          "label": "主要问题摘要",
          "type": "long_text",
          "required": false,
          "sensitive": true
        },
        {
          "id": "maintaining_factors",
          "label": "可能的维持因素",
          "type": "long_text",
          "required": false,
          "sensitive": true
        },
        {
          "id": "case_conceptualization_hypothesis",
          "label": "初步个案概念化假设",
          "type": "long_text",
          "required": false,
          "sensitive": true
        },
        {
          "id": "clinical_risk_judgment",
          "label": "初步风险判断",
          "type": "long_text",
          "required": false,
          "sensitive": true
        },
        {
          "id": "referral_recommendation",
          "label": "是否建议转介或联合精神科评估",
          "type": "long_text",
          "required": false,
          "sensitive": true
        },
        {
          "id": "next_session_focus",
          "label": "下次访谈重点",
          "type": "long_text",
          "required": false,
          "sensitive": true
        },
        {
          "id": "counselor_remarks",
          "label": "咨询师备注",
          "type": "long_text",
          "required": false,
          "sensitive": true
        }
      ]
    }
  ]
}
```

## Agent 输出规则草案

当用户输入“给我一个初访信息收集表”或语义相近请求时，Agent 应：

1. 询问使用对象：咨询师访谈使用、来访者预填写使用，还是系统字段导出。
2. 如果用户未指定，默认输出“咨询师访谈版”。
3. 如果用户要求“完整 MVP”或“全部版本”，输出三个版本。
4. 输出时提醒：表单用于专业辅助，不替代咨询师判断。
5. 对风险评估部分保持明确、谨慎，不弱化自伤、自杀、他伤、虐待和现实检验相关问题。

## 后续可扩展能力

- 将 JSON Schema 转为前端表单配置。
- 将表单结果转为初访评估摘要。
- 将表单结果输入个案概念化 Agent。
- 将表单结果输入风险评估 Agent。
- 将表单结果生成咨询记录、阶段报告、转介建议或结案报告。
