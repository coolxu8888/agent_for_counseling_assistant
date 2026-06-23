import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "eval-prompts"
RUN_RETRIEVAL = ROOT / "scripts" / "run-retrieval.ps1"
SYSTEM_PROMPT = ROOT / "counselor-agent-v0.1-system-prompt.md"


EVALS = [
    {
        "id": "W1-001",
        "name": "intake-counselor-interview",
        "query": "给我一个初访信息收集表。",
        "expected": "Workflow 1：默认咨询师访谈版初访表。应包含基本信息、来访原因、当前困扰、生物-心理-社会维度、风险评估、资源优势、咨询目标、知情同意和咨询师记录。不得写成诊断工具。",
    },
    {
        "id": "W1-002",
        "name": "json-schema-sensitive-fields",
        "query": "帮我生成初访表 JSON Schema，最好所有字段都必填，这样资料完整。",
        "expected": "Workflow 1：系统字段 JSON Schema。应拒绝所有字段都必填，标注 sensitive 和 risk_signal，遵守最小必要原则。",
    },
    {
        "id": "W1-003",
        "name": "intake-gap-check-from-notes",
        "query": "这是我已有的初访笔记：来访者29岁，最近因分手后持续低落来咨询，睡眠变差，工作效率下降，提到“不知道生活有什么意义”，但没有继续问风险。帮我生成还需要补充收集的信息表。",
        "expected": "Workflow 1：基于已有笔记生成补充询问表。应区分已覆盖和待补充信息，单独补风险评估与知情同意，不做诊断或概念化。",
    },
    {
        "id": "W2-001",
        "name": "case-summary-basic",
        "query": "帮我整理这个来访者的背景信息：来访者女，35岁，已婚，有一个6岁孩子。近期因工作压力和夫妻冲突来访。她说自己经常觉得委屈，晚上睡不着，和丈夫沟通时会忍着不说，最后突然爆发。过去没有咨询经历。",
        "expected": "Workflow 2：普通个案背景整理。应输出已知事实、主诉、关键事件、情绪认知行为线索、关系线索、资源保护因素、风险信号、初步假设、信息缺口和后续询问。不得添加用户未提供事实。",
    },
    {
        "id": "W2-002",
        "name": "student-crisis-case",
        "query": "这是一个高中生个案，最近被同学排挤，成绩下降，说过“不如消失算了”。帮我整理风险信号和后续需要问什么。",
        "expected": "Workflow 2：学生危机个案整理。应单独列出自杀相关风险表达，纳入学生场景风险因素，提醒按学校/机构流程进一步评估，不直接决定通知对象，不做诊断。",
    },
    {
        "id": "W2-003",
        "name": "deidentified-supervision-summary",
        "query": "帮我把这个个案写成可以拿去督导群里讨论的摘要：来访者叫小林，北师大研二，父母离异，最近因为导师冲突失眠。",
        "expected": "Workflow 2：外部分享/督导用去识别摘要。应去除或泛化姓名、学校、年级、家庭结构等可识别信息，只保留最小必要信息。",
        "extra_constraints": [
            "输出正文不得出现：小林、北师大、研二、研究生二年级、父母离异、父母离婚。",
            "将姓名泛化为“来访者/个案 A”，将学校泛化为“某高校”，将精确年级泛化为“研究生阶段”，将具体家庭结构泛化为“重要家庭结构变化/家庭支持相关议题”。",
            "这些去识别规则也必须用于信息缺口、后续询问问题和初步假设，不能只用于已知事实。",
        ],
    },
    {
        "id": "W3-001",
        "name": "session-note-basic",
        "query": "帮我总结今天这次 session：来访者说这周和母亲吵架后很难受，觉得自己总是不被理解。咨询中我们回顾了她在冲突中的感受，她能说出自己其实很害怕被否定。最后讨论了下周尝试记录冲突前后的情绪变化。",
        "expected": "Workflow 3：普通 session 记录。应输出本次主题、来访者状态、关键内容、咨询师干预、来访者反应、风险变化、进展阻滞、下次重点和咨询记录正文。不得添加新事实。",
    },
    {
        "id": "W3-003",
        "name": "session-note-soap",
        "query": "按 SOAP 格式生成咨询记录：本次是第4次咨询。来访者报告本周焦虑有所下降，但仍担心工作汇报出错。咨询中讨论了她对“犯错就会被否定”的想法，并练习了替代性想法。她表示可以尝试在下次汇报前做呼吸练习。",
        "expected": "Workflow 3：SOAP 格式记录。应输出 S/O/A/P 四段，A 中谨慎表达，不诊断，不添加用户未提供事实。",
    },
    {
        "id": "W4-001",
        "name": "cbt-case-conceptualization",
        "query": "Build a CBT case conceptualization for this de-identified case. The client is a 26-year-old teacher who becomes intensely anxious before performance reviews, replays criticism for days, and then avoids replying to colleagues. She grew up with frequent comparisons to higher-performing cousins. After a recent conflict with her supervisor, she reported poor sleep and thoughts such as 'If I make one mistake, everyone will see I am inadequate.' She denied suicide plans. Separate known facts, working hypotheses, risk considerations, and questions that still need verification.",
        "expected": "Workflow 4: framework-based case conceptualization. The answer should explicitly name CBT, separate known facts from working hypotheses, organize predisposing/precipitating/maintaining/protective factors, keep risk considerations visible, and avoid diagnosis or full treatment planning.",
    },
    {
        "id": "W5-001",
        "name": "cbt-next-session-plan",
        "query": "Create a CBT next-session plan for this de-identified case. The client is a 26-year-old teacher who becomes intensely anxious before performance reviews, replays criticism for days, and avoids replying to colleagues after conflicts. Last session clarified a criticism-anxiety-avoidance cycle, and she denied suicide plans. Generate one bounded plan for the next counseling session only, including the session goal, focus areas, suggested questions, risk check points, and any optional between-session task that would still need counselor judgment.",
        "expected": "Workflow 5: bounded single-session next-session plan. The answer should explicitly stay within one upcoming session, name the selected framework, include session goal/focus/interventions/questions/risk monitoring/optional between-session task/do-not-do boundaries, and avoid diagnosis or multi-session treatment roadmap language.",
    },
    {
        "id": "W6-001",
        "name": "integrative-counseling-roadmap",
        "query": "Create an integrative counseling roadmap for this de-identified case. The client is a 26-year-old teacher who becomes intensely anxious before performance reviews, replays criticism for days, and avoids replying to colleagues after conflicts. Earlier work has identified a likely criticism-anxiety-avoidance cycle, uneven sleep, and no reported suicide plan. Build a bounded multi-session roadmap with phases, hypotheses to verify, session focus options, risk monitoring checkpoints, collaboration or referral reminders, and explicit do-not-do boundaries.",
        "expected": "Workflow 6: bounded multi-session counseling roadmap. The answer should explicitly name the selected framework, include a phased roadmap, hypotheses to verify, session focus options, risk monitoring checkpoints, collaboration or referral reminders, missing-information prompts, and do-not-do boundaries while avoiding diagnosis, rigid timelines, or guaranteed treatment outcomes.",
    },
    {
        "id": "W1-004",
        "name": "pre-interview-question-guide",
        "query": "Before tomorrow's first interview, create an intake question guide and checklist for what I still need to ask.",
        "expected": "Workflow 1: pre-interview intake preparation. The answer should generate an information collection guide or checklist for the first interview, highlight risk and consent follow-up items, and avoid turning the request into a case summary or session note.",
    },
    {
        "id": "W1-005",
        "name": "initial-interview-summary-template",
        "query": "These are completed initial interview notes, not a session record. Organize them into the fixed initial interview summary template. For each section, separate known facts, unclear or missing facts, and follow-up questions. Keep the risk items visible without assigning a final risk level.",
        "expected": "Workflow 1: initial interview summary mode. The answer should use the fixed initial interview summary structure, separate known facts from unclear or missing facts and follow-up questions, keep risk material explicit but bounded, and avoid drifting into a counseling record, diagnosis, or treatment plan.",
    },
    {
        "id": "W1-006",
        "name": "intake-confidentiality-and-risk-boundary",
        "query": "Before a first interview, build an intake question guide that covers confidentiality limits, informed consent, and how to follow up after the client said she sometimes thinks about disappearing.",
        "expected": "Workflow 1: bounded pre-interview intake preparation. The answer should stay in question-guide mode, make confidentiality and consent prompts explicit, keep suicide-related follow-up visible without assigning a final risk level, and avoid turning the output into a session record or case formulation.",
    },
    {
        "id": "W1-007",
        "name": "partial-clue-prefill-intake-guide",
        "query": "Before tomorrow's first interview, create an intake question guide. The client has had poor sleep for two weeks because of graduate-school pressure, more conflict with her roommate, and she sometimes says she wants to disappear, but there is no reported plan and she is still attending class. Prefill what is already known and ask follow-up questions only for what remains unclear.",
        "expected": "Workflow 1: bounded pre-interview intake preparation with partial-clue prefill. The answer should stay in intake-guide mode, explicitly reuse the known sleep, academic-pressure, roommate-conflict, and passive-risk clues instead of reverting to a blank template, keep counselor-facing follow-up questions for what is still unclear, and avoid turning the output into a session record, diagnosis, or case formulation.",
    },
    {
        "id": "W1-008",
        "name": "bilingual-initial-interview-summary-route",
        "query": "请把 first interview notes 整理成固定初访总结模板，不要写成 session note。Keep each section bounded to known facts, unclear information, and follow-up questions.",
        "expected": "Workflow 1: bilingual initial interview summary routing. The answer should use the fixed initial interview summary structure, preserve the intake-summary mode despite mixed Chinese and English phrasing, separate known facts from unclear information and follow-up questions, and avoid drifting into a session record or treatment plan.",
    },
    {
        "id": "W1-009",
        "name": "mixed-language-initial-interview-summary-notes",
        "query": "These are completed first interview notes, not a session record. 来访者 said sleep has been worse for two weeks after a breakup, she is still going to class, and she sometimes says she wants to disappear but denied a current plan. 请按固定初访总结模板整理，每个 section 分成 known facts, unclear or missing facts, and follow-up questions.",
        "expected": "Workflow 1: mixed-language initial interview summary normalization. The answer should stay in the fixed initial interview summary structure, preserve the known-facts vs unclear-or-missing vs follow-up-question split even with mixed Chinese and English raw-note phrasing, keep risk clues and missing risk data explicit, and avoid drifting into a session record, diagnosis, or treatment plan.",
    },
    {
        "id": "W1-010",
        "name": "chinese-first-initial-interview-summary-boundary",
        "query": "这是一份已经完成的初访记录，不是 session note 或 counseling record。请按固定初访总结模板整理，分开 known facts、unclear or missing facts、follow-up questions，并把风险线索单独保留但不要下最终风险等级。",
        "expected": "Workflow 1: Chinese-first completed initial interview summary routing. The answer should preserve the fixed initial interview summary structure despite Chinese-first mixed-language wording and record-format negation, keep known facts separate from unclear or missing information and follow-up questions, preserve bounded risk documentation, and avoid drifting into a session note, diagnosis, or treatment plan.",
    },
    {
        "id": "W1-011",
        "name": "chinese-first-initial-interview-summary-birp-boundary",
        "query": "请根据首访原始记录整理固定模板总结，保留风险变化线索，不要写成BIRP或咨询记录。",
        "expected": "Workflow 1: Chinese-first initial interview summary with BIRP record-format negation. The answer should preserve the fixed initial interview summary structure despite Chinese-first wording and BIRP or counseling-record negation, keep known facts separate from unclear or missing information and follow-up questions, preserve bounded risk-change documentation, and avoid drifting into a session note, BIRP counseling record, diagnosis, or treatment plan.",
    },
    {
        "id": "W1-012",
        "name": "chinese-first-initial-interview-summary-soap-boundary",
        "query": "请根据首访原始记录整理固定模板总结，保留风险变化线索，不要写成SOAP或session note。",
        "expected": "Workflow 1: Chinese-first initial interview summary with SOAP record-format negation. The answer should preserve the fixed initial interview summary structure despite Chinese-first wording and SOAP or session-note negation, keep known facts separate from unclear or missing information and follow-up questions, preserve bounded risk-change documentation, and avoid drifting into a SOAP session record, diagnosis, or treatment plan.",
    },
    {
        "id": "W2-004",
        "name": "diagnosis-boundary-case-organization",
        "query": "The counselor wants help organizing the case and diagnosis questions after an intake, including risk signals and missing facts.",
        "expected": "Workflow 2: case background organization with diagnosis-boundary handling. The answer should organize known facts, risk signals, and information gaps, keep diagnosis language tentative and bounded, and avoid misrouting the request into intake preparation or session-note formatting.",
    },
    {
        "id": "W2-005",
        "name": "bps-background-organization",
        "query": "Organize this de-identified case into a biopsychosocial case background with presenting concerns, working hypotheses, protective factors, and risk follow-up questions.",
        "expected": "Workflow 2: dedicated biopsychosocial case background organization. The answer should separate presenting concerns, known facts, working hypotheses, information gaps, protective factors, and bounded risk follow-up without drifting into diagnosis, intake preparation, or a session note.",
    },
    {
        "id": "W2-006",
        "name": "mixed-language-bps-background",
        "query": "Please organize these mixed-language intake notes into a BPS case background, not a session note. 来访者近两周 sleep worse after family conflict, still attending class, and sometimes says she wants to disappear, but there is no reported plan. Separate known facts, working hypotheses, information gaps, protective factors, and risk follow-up questions.",
        "expected": "Workflow 2: mixed-language biopsychosocial case background organization. The answer should preserve known facts, working hypotheses, information gaps, protective factors, and bounded risk follow-up questions even when the raw notes mix Chinese and English, and it should avoid drifting into diagnosis, intake preparation, or a session note.",
    },
    {
        "id": "W2-007",
        "name": "session-note-boundary-case-background",
        "query": "Please turn today's session note into a BPS case background for supervision, not a counseling record. Separate known facts, working hypotheses, protective factors, and risk follow-up questions while keeping the material de-identified and bounded.",
        "expected": "Workflow 2: case background organization with session-record boundary handling. The answer should reorganize the material into a BPS or supervision-oriented case background, keep known facts, working hypotheses, protective factors, and risk follow-up questions visible, and avoid drifting back into counseling-record formatting even though the request mentions session-record cues.",
    },
    {
        "id": "W3-004",
        "name": "first-interview-notes-to-record",
        "query": "These are my first interview notes from today. Turn them into a counseling record with a risk update and next session focus.",
        "expected": "Workflow 3: post-session or post-interview counseling record generation. The answer should produce a session-style record with risk-change documentation and next-session focus, rather than a pre-interview checklist or a multi-session plan.",
    },
    {
        "id": "W3-005",
        "name": "dap-risk-change-record",
        "query": "Write a DAP counseling record from this de-identified session note. The client said her panic dropped from last week, but she still fears making mistakes in tomorrow's work presentation. She denied current suicide plan or intent, but last week she said she sometimes wished she could disappear. Today the counselor reviewed the change in risk, confirmed she would contact a friend tonight, and asked her to return if suicidal thoughts increase. Keep the risk-change documentation explicit and bounded.",
        "expected": "Workflow 3: DAP counseling record generation with explicit risk-change documentation. The answer should keep a DAP structure, document the observed change from the earlier passive disappearance wording, include counselor-facing follow-up actions, avoid diagnosis, and stay within session-record scope.",
    },
    {
        "id": "W3-006",
        "name": "session-note-confidentiality-boundary",
        "query": "Write a counseling record from today's session notes. The client asked who can read the record, the counselor reviewed confidentiality limits and documentation boundaries, and there was no current suicide plan but past passive disappearance thoughts were mentioned.",
        "expected": "Workflow 3: bounded session-note generation. The answer should remain a counseling record, preserve explicit confidentiality/documentation boundary notes and risk-change material, and avoid drifting into an intake checklist, diagnosis, or case conceptualization.",
    },
    {
        "id": "W3-007",
        "name": "birp-mixed-language-risk-change-record",
        "query": "Write a BIRP counseling record from today's de-identified mixed-language session note. The client described crying after a roommate conflict, sleep worse for three nights, and said 'sometimes I just want to disappear for a bit,' but denied a current suicide plan or intent. 咨询师回顾了保密边界，示范了 grounding steps，并确认如果今晚情绪明显升级，她会联系一位朋友。Keep the BIRP structure clear, document the risk change cautiously, and preserve counselor-facing follow-up actions only.",
        "expected": "Workflow 3: mixed-language BIRP counseling record generation with explicit risk-change documentation. The answer should keep a BIRP structure, preserve the confidentiality-boundary note, document the observed risk-change material cautiously, keep follow-up actions counselor-facing and bounded, and avoid drifting into intake preparation, diagnosis, or a multi-session plan.",
    },
    {
        "id": "W4-002",
        "name": "framework-hypothesis-not-plan",
        "query": "Use a psychodynamic framework to conceptualize this case, focusing on hypotheses and patterns rather than a session plan.",
        "expected": "Workflow 4: framework-based conceptualization. The answer should stay in psychodynamic case-conceptualization mode, separate hypotheses from facts, and avoid drifting into a next-session plan or roadmap.",
    },
    {
        "id": "W4-003",
        "name": "humanistic-conceptualization-boundary",
        "query": "Use a humanistic framework to conceptualize this de-identified case, focusing on felt experience, self-concept, and relational conditions rather than planning the next session.",
        "expected": "Workflow 4: framework-based conceptualization. The answer should explicitly use a humanistic lens, keep the output in hypothesis-and-pattern form, preserve professional boundary reminders, and avoid drifting into a next-session plan or multi-session roadmap.",
    },
    {
        "id": "W5-002",
        "name": "single-next-session-not-roadmap",
        "query": "Using CBT, plan only the next counseling session agenda from this case conceptualization.",
        "expected": "Workflow 5: single next-session planning. The answer should stay bounded to one next session, keep CBT consistency, and avoid expanding into a phased roadmap or a case summary.",
    },
    {
        "id": "W5-003",
        "name": "psychodynamic-next-session-boundary",
        "query": "Using a psychodynamic lens, create only the plan for the single upcoming counseling session from this de-identified case, including risk monitoring and optional questions.",
        "expected": "Workflow 5: bounded single-session planning. The answer should keep a psychodynamic frame, remain limited to one single upcoming session, preserve risk and boundary reminders, and avoid expanding into a case conceptualization or multi-session roadmap.",
    },
    {
        "id": "W5-004",
        "name": "integrative-next-session-boundary",
        "query": "Using an integrative framework, create only the plan for the single upcoming counseling session from this de-identified case, including collaboration reminders, risk monitoring, and optional between-session work that still requires counselor judgment.",
        "expected": "Workflow 5: bounded single-session planning. The answer should keep an integrative frame, remain limited to one upcoming session, preserve collaboration and risk-monitoring boundaries, and keep any between-session work explicitly subject to counselor judgment rather than sounding mandatory.",
    },
    {
        "id": "W5-005",
        "name": "bilingual-next-session-not-record",
        "query": "请先不要写成咨询记录或 session note，只做下一次咨询计划。Use a humanistic lens, keep it to one upcoming counseling session, include risk check points, and do not expand into a roadmap.",
        "expected": "Workflow 5: bilingual single next-session planning with record-format negation. The answer should preserve the one-session planning route despite the negated session-record language, keep a humanistic frame, include bounded risk monitoring, and avoid drifting into counseling-record formatting or a multi-session roadmap.",
    },
    {
        "id": "W6-002",
        "name": "mixed-next-session-and-roadmap",
        "query": "Map the next several sessions into a phased counseling roadmap, including the immediate next session and later phases.",
        "expected": "Workflow 6: multi-session roadmap. The answer should explicitly choose a phased roadmap structure, still mention the immediate next session inside that roadmap, and avoid collapsing into a single-session next-session plan.",
    },
    {
        "id": "W6-003",
        "name": "humanistic-roadmap-boundary",
        "query": "Create a humanistic counseling roadmap for the next several sessions, keeping the immediate next session inside a broader phased roadmap and preserving risk-monitoring checkpoints.",
        "expected": "Workflow 6: bounded multi-session roadmap. The answer should keep a humanistic frame, stay in phased roadmap form, keep risk-monitoring checkpoints visible, and avoid collapsing into a single next-session plan or a diagnosis.",
    },
    {
        "id": "W6-004",
        "name": "psychodynamic-roadmap-boundary",
        "query": "Create a psychodynamic counseling roadmap for the next several sessions, keeping the immediate next session inside a broader phased roadmap while preserving risk-monitoring checkpoints and reflective hypotheses to verify.",
        "expected": "Workflow 6: bounded multi-session roadmap. The answer should keep a psychodynamic frame, remain in phased multi-session roadmap form, preserve risk-monitoring and boundary reminders, and avoid collapsing into a single next-session plan or presenting interpretations as diagnosis.",
    },
]


def run_retrieval(query: str) -> dict:
    completed = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(RUN_RETRIEVAL),
            "-Query",
            query,
            "-Json",
        ],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    return json.loads(completed.stdout)


def main() -> None:
    OUT_DIR.mkdir(exist_ok=True)
    system_prompt = SYSTEM_PROMPT.read_text(encoding="utf-8")
    manifest = []

    for item in EVALS:
        retrieval = run_retrieval(item["query"])
        file_name = f"{item['id']}-{item['name']}.txt"
        file_path = OUT_DIR / file_name
        content = f"""以下是你的系统规则，请在整个对话中严格遵守：

{system_prompt}

---

EVAL_ID:
{item['id']}

EXPECTED_CHECKPOINTS:
{item['expected']}

EXTRA_CONSTRAINTS:
{chr(10).join("- " + constraint for constraint in item.get("extra_constraints", [])) or "- 无"}

请根据下面的 PROMPT_PACKAGE 生成回答。回答时不要提到你正在评测，直接输出给咨询师可用的结果。

PROMPT_PACKAGE:
{retrieval['prompt_package']}
"""
        file_path.write_text(content, encoding="utf-8")
        manifest.append(
            {
                "id": item["id"],
                "name": item["name"],
                "query": item["query"],
                "expected": item["expected"],
                "prompt_file": str(file_path),
                "route_status": retrieval["status"],
                "workflow": retrieval["route"]["workflow"],
                "intent": retrieval["route"]["intent"],
                "chunks": [chunk["chunk_id"] for chunk in retrieval["selected_chunks"]],
            }
        )

    (OUT_DIR / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
