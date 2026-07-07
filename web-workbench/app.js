const state = {
  workflow: "AUTO",
  runDir: null,
  structuredOutput: null,
  lastRunData: null,
  templateSlots: [],
  demoCatalog: null,
  user: null,
  locale: "zh-CN",
  workspaceGovernance: null,
  authConfig: { signup_enabled: false, invite_required: false },
  authMode: "login",
  caseId: "",
  caseDetail: null,
  selectedTemplateRef: "",
  selectedTemplateLabel: "",
  workspacePolicy: { max_upload_bytes: 10 * 1024 * 1024, retention_days: null, reset_enabled: true },
  deploymentReadiness: null,
};

const FALLBACK_DEMO_CATALOG = {
  scenarios: [
    {
      id: "case-family-boundary",
      title: "Recommended demo: W2 case background",
      workflow: "W2",
      summary: "A de-identified biopsychosocial case background request focused on family pressure, protective factors, and uncertainty.",
      input:
        "请整理个案信息。来访者 24 岁，刚入职，最近半年经常因父母催婚和工作绩效焦虑失眠，上周和父亲争执后独自喝了很多酒，但否认自伤想法。已进行过两次校外咨询，目前最困扰的是情绪波动、注意力下降和回避与家人沟通。请区分已知事实、推测和待补充信息。",
      output_style: "supervision_summary",
    },
    {
      id: "intake_sleep-stress",
      title: "W1 Demo: Initial interview prep",
      workflow: "W1",
      summary: "A de-identified intake request with sleep issues, family stress, and a mild risk prompt.",
      input:
        "请帮我生成初访信息收集表。来访者为大学女生，近两周因保研压力睡眠变差，和室友关系紧张，偶尔说“想消失一下”，但没有计划，也愿意继续上课。咨询师希望准备首访提问提纲，并单独标出需要进一步核实的风险与保护因素。",
      output_style: "professional_concise",
    },
    {
      id: "initial-interview-material-to-bps-background",
      title: "W2 Demo: Intake material to BPS background",
      workflow: "W2",
      summary: "A boundary case where completed first-interview material should be reorganized into a supervision-oriented BPS background rather than kept in the fixed W1 summary template.",
      input:
        "These are completed first interview notes. Organize them into a BPS case background for supervision, keep known facts, working hypotheses, protective factors, and risk follow-up questions visible, and do not keep the fixed initial interview summary template.",
      output_style: "supervision_summary",
    },
    {
      id: "chinese-intake-material-to-bps-background",
      title: "W2 Demo: Chinese intake material to BPS background",
      workflow: "W2",
      summary: "A Chinese-heavy boundary case where first-interview material should be rewritten into a supervision-oriented BPS case background instead of staying in the fixed W1 summary template.",
      input:
        "把这份首访材料改写成督导讨论用的个案背景，按BPS整理已知事实、信息缺口、保护因素和风险追问，而不是固定初访总结模板。",
      output_style: "supervision_summary",
    },
    {
      id: "loose-intake-summary-negation-to-bps-background",
      title: "W2 Demo: Loose intake-summary negation",
      workflow: "W2",
      summary: "A looser W1-vs-W2 boundary where completed intake notes should become a supervision BPS background instead of staying in the usual initial interview summary format.",
      input:
        "Use these completed intake notes to build a supervision case background with BPS, known facts, protective factors, and risk follow-up questions. Do not keep it as the usual initial interview summary.",
      output_style: "supervision_summary",
    },
    {
      id: "chinese-loose-intake-summary-negation-to-bps-background",
      title: "W2 Demo: Chinese loose intake-summary negation",
      workflow: "W2",
      summary: "A Chinese-heavy loose-negation boundary where completed intake material should become a supervision BPS background instead of staying in the usual initial interview summary.",
      input:
        "请把这份已完成的首访材料整理成督导讨论用的个案背景，按BPS梳理已知事实、信息缺口、保护因素和风险追问，不要还是按常规初访总结。",
      output_style: "supervision_summary",
    },
    {
      id: "regular-intake-summary-negation-to-bps-background",
      title: "W2 Demo: Regular intake-summary negation",
      workflow: "W2",
      summary: "A supervision boundary where completed intake materials should become a BPS case background instead of staying in the regular initial interview summary.",
      input:
        "Please organize these completed intake materials into a BPS supervision case background with confidentiality limits, risk follow-up questions, and protective factors; this is for case discussion, not the regular initial interview summary.",
      output_style: "supervision_summary",
    },
    {
      id: "standard-risk-block-negation-to-bps-background",
      title: "W2 Demo: Standard risk-block negation",
      workflow: "W2",
      summary: "A mixed-risk boundary where completed first-interview material should become a supervision BPS background instead of staying in the standard intake-summary risk block.",
      input:
        "Use completed first interview material to write a supervision case background with protective factors and risk follow-up questions, not the standard initial interview summary risk block.",
      output_style: "supervision_summary",
    },
    {
      id: "bilingual-risk-block-negation-to-bps-background",
      title: "W2 Demo: Bilingual risk-block negation",
      workflow: "W2",
      summary: "A bilingual mixed-risk boundary where completed first-interview material should become a supervision case background instead of going back into the standard intake-summary risk block.",
      input:
        "请把已完成的首访材料整理成督导 case background，保留 protective factors 和 risk follow-up questions，不要把它放回 standard initial interview summary risk block。",
      output_style: "supervision_summary",
    },
    {
      id: "session-sleep-communication",
      title: "W3 Demo: Session note",
      workflow: "W3",
      summary: "A de-identified session note request with clear theme, intervention focus, and risk boundary.",
      input:
        "来访者表示最近一周入睡困难，和母亲沟通后感到委屈，否认自伤自杀计划。本次主要讨论情绪识别与下次沟通准备。请生成本次咨询记录，并保留需要后续补充的信息。",
      output_style: "institutional_record",
    },
    {
      id: "session-dap-risk-change",
      title: "W3 Demo: DAP risk update",
      workflow: "W3",
      summary: "A de-identified DAP record request that emphasizes bounded risk-change documentation and counselor follow-up actions.",
      input:
        "请根据以下去识别化会谈笔记写一份 DAP 咨询记录：来访者说与上周相比惊恐下降了一些，但仍担心明天的工作汇报会出错。她否认当前有自杀计划或意图，但上周提过“有时想消失一下”。本次咨询中，咨询师回顾了风险变化，确认她今晚会联系一位朋友，并说明如果自杀想法加重需要及时回访。请把风险变化记录写清楚，但保持边界和谨慎表达。",
      output_style: "institutional_record",
    },
    {
      id: "session-birp-risk-change",
      title: "W3 Demo: BIRP record",
      workflow: "W3",
      summary: "A de-identified BIRP record request with mixed-language note fragments, confidentiality boundary reminders, and explicit risk-change follow-up.",
      input:
        "Write a BIRP counseling record from today's de-identified session note. The client described crying after a roommate conflict, sleep worse for three nights, and said 'sometimes I just want to disappear for a bit,' but denied a current suicide plan or intent. 咨询师回顾了保密边界，示范了 grounding steps，并确认如果今晚情绪明显升级，她会联系一位朋友。Keep the BIRP structure clear, document the risk change cautiously, and preserve counselor-facing follow-up actions only.",
      output_style: "institutional_record",
    },
    {
      id: "conceptualization-criticism-cycle",
      title: "W4 Demo: CBT conceptualization",
      workflow: "W4",
      summary: "A de-identified framework-specific conceptualization request for supervision-style review.",
      input:
        "Build a CBT case conceptualization for this de-identified case. The client is a 26-year-old teacher who becomes intensely anxious before performance reviews, replays criticism for days, and then avoids replying to colleagues. She grew up with frequent comparisons to higher-performing cousins. After a recent conflict with her supervisor, she reported poor sleep and thoughts such as 'If I make one mistake, everyone will see I am inadequate.' She denied suicide plans. Separate known facts, working hypotheses, risk considerations, and questions that still need verification.",
      output_style: "supervision_summary",
    },
    {
      id: "conceptualization-bilingual-session-note-boundary",
      title: "W4 Demo: Bilingual session-note to conceptualization",
      workflow: "W4",
      summary: "A bilingual boundary case where today's session note is only source material for a CBT conceptualization rather than a counseling record.",
      input:
        "请根据今天session note整理CBT概念化，保留working hypotheses，不要写成咨询记录。Separate known facts, working hypotheses, risk considerations, and questions that still need verification.",
      output_style: "supervision_summary",
    },
    {
      id: "next-session-criticism-cycle",
      title: "W5 Demo: Next-session plan",
      workflow: "W5",
      summary: "A bounded single-session planning request that stays framework-aware without turning into a roadmap.",
      input:
        "Create a CBT next-session plan for this de-identified case. The client is a 26-year-old teacher who becomes intensely anxious before performance reviews, replays criticism for days, and avoids replying to colleagues after conflicts. Last session clarified a criticism-anxiety-avoidance cycle, and she denied suicide plans. Generate one bounded plan for the next counseling session only, including the session goal, focus areas, suggested questions, risk check points, and any optional between-session task that would still need counselor judgment.",
      output_style: "supervision_summary",
    },
    {
      id: "roadmap-criticism-cycle",
      title: "W6 Demo: Counseling roadmap",
      workflow: "W6",
      summary: "A bounded multi-session roadmap request that stays framework-aware without turning into a rigid treatment prescription.",
      input:
        "Create an integrative counseling roadmap for this de-identified case. The client is a 26-year-old teacher who becomes intensely anxious before performance reviews, replays criticism for days, and avoids replying to colleagues after conflicts. Earlier work identified a likely criticism-anxiety-avoidance cycle, poor sleep after supervisor conflicts, and no reported suicide plan. Build a bounded roadmap with phases, hypotheses to verify, session focus options, risk monitoring checkpoints, collaboration or referral reminders, and explicit do-not-do boundaries.",
      output_style: "supervision_summary",
    },
    {
      id: "roadmap-bilingual-session-note-source-material",
      title: "W6 Demo: Bilingual session-note to roadmap",
      workflow: "W6",
      summary: "A bilingual boundary case where today's session note is only source material for a phased multi-session roadmap rather than a counseling record.",
      input:
        "请把今天的session note作为素材，整理接下来几次咨询的路线图，包含 immediate next session 和 later phases，保留风险检查点，不要写成咨询记录。",
      output_style: "supervision_summary",
    },
  ],
  templates: [],
  privacy_notice: "Use de-identified demo material only. Avoid names, phone numbers, IDs, and real client data in public MVP validation.",
};

const $ = (id) => document.getElementById(id);
const INTRO_KEY = "counselor_agent_intro_seen";
const SIDE_COLLAPSED_KEY = "counselor_agent_side_collapsed";
const SIDE_WIDTH_KEY = "counselor_agent_side_width";
const LOGIN_USERNAME_KEY = "counselor_agent_login_username";
const LOCALE_KEY = "counselor_agent_locale";
const DEFAULT_LOCALE = "zh-CN";
const SUPPORTED_LOCALES = ["zh-CN", "en"];
const MESSAGES = {
  "zh-CN": {
    "common.none": "无",
    "intro.badge": "Counselor Assistant",
    "intro.title": "一次粘贴咨询材料，剩下交给工作台自动分流。",
    "intro.body": "这个产品可以准备首访信息收集提纲、整理已完成的初访记录、组织生物心理社会背景、生成咨询记录、输出理论取向个案概念化，并在可见的隐私与审阅边界下完成 Word 模板填充。",
    "intro.roll.w1": "首访准备",
    "intro.roll.w2": "个案背景整理（BPS）",
    "intro.roll.w3": "咨询记录生成",
    "intro.roll.w4": "CBT 个案概念化",
    "intro.roll.w5": "下次会谈计划",
    "intro.roll.w6": "多次会谈路线图",
    "intro.roll.risk": "风险边界提醒",
    "intro.roll.upload": "Word 模板上传",
    "intro.roll.scan": "模板槽位扫描",
    "intro.roll.history": "运行历史与导出",
    "intro.roll.gov": "工作台治理",
    "intro.open": "进入工作台",
    "intro.skip": "跳过介绍",
    "login.kicker": "中文优先",
    "login.title": "咨询师工作台登录",
    "login.body": "先用去标识化材料做验证。默认测试账号可直接进入，后续再替换为正式工作台账户。",
    "login.demo.label": "测试账号",
    "login.demo.value": "demo / demo123",
    "login.username": "用户名",
    "login.usernamePlaceholder": "输入用户名",
    "login.password": "密码",
    "login.passwordPlaceholder": "输入密码",
    "login.confirmPassword": "确认密码",
    "login.confirmPasswordPlaceholder": "再次输入密码",
    "login.inviteCode": "邀请码",
    "login.inviteCodePlaceholder": "输入邀请码",
    "login.submit": "登录",
    "login.replay": "重新看介绍",
    "topbar.brand": "Counselor Assistant",
    "topbar.caption": "将咨询任务路由成结构化草稿、记录、导出和模板结果。",
    "topbar.logout": "退出登录",
    "workflow.AUTO": "自动识别",
    "workflow.W1": "首访准备 / 首访总结",
    "workflow.W2": "个案背景（BPS）",
    "workflow.W3": "咨询记录",
    "workflow.W4": "个案概念化",
    "workflow.W5": "下次会谈计划",
    "workflow.W6": "咨询路线图",
    "workflow.TEMPLATE": "模板起草",
    "auth.mode.login": "登录",
    "auth.mode.signup": "创建工作台",
    "auth.hint.loginOnly": "请使用当前分配的工作台账号登录。",
    "auth.hint.loginOrSignup": "可以直接登录，也可以为试用创建独立工作台账号。",
    "auth.hint.signupInvite": "使用部署邀请码创建一个隔离的咨询师工作台。",
    "auth.hint.signupOpen": "在当前部署上创建一个隔离的咨询师工作台。",
    "auth.pending.login": "正在登录...",
    "auth.pending.signup": "正在创建工作台...",
    "auth.signedInAs": "已登录：{username}",
    "auth.signedOut": "已退出登录。",
    "demo.library": "演示资料库",
    "demo.signIn": "登录后可加载一键演示案例和内置模板。",
    "demo.scenariosPlaceholder": "这里会显示去标识化的示例工作流。",
    "demo.templatesPlaceholder": "这里会显示内置 Word 模板。",
    "demo.loadedWorkflow": "已加载 {workflow} 示例",
    "demo.loadedScenario": "已加载演示场景：{title}。",
    "demo.sampleLoaded": "{title}\n\n{summary}\n\n示例输入已填入编辑区。检查后点击“运行”即可发起真实模型调用。",
    "demo.templateLoaded": "已选择内置模板：{title}。现在可以扫描槽位或开始起草。",
    "demo.loadSample": "加载示例",
    "demo.useTemplate": "使用模板",
    "demo.noneScenario": "当前环境没有可用的演示场景。",
    "demo.noneTemplate": "当前环境没有找到内置 Word 模板。",
    "demo.privacy": "只使用去标识化演示材料。不要输入真实姓名、电话、证件号或完整个案信息。",
    "account.title": "工作台账号",
    "account.signedOut": "登录后可查看当前工作台账号，并在需要时轮换密码。",
    "account.signedIn": "当前账号：{username}。在交接咨询师或凭证变更后，请及时轮换工作台密码。",
    "governance.title": "数据控制",
    "governance.signedOut": "先检查存储、上传上限和保留策略，再用托管环境做试点验证。",
    "deployment.title": "部署就绪度",
    "deployment.signedOut": "登录后可查看模型访问、工作台认证、保留策略和存储持久性。",
    "intent.title": "意图路由",
    "intent.empty": "每次运行后，这里会显示系统识别到的咨询任务类型。",
    "intent.routeStatus": "{prefix} | 路由状态：{status}。",
    "intent.completed": "{prefix} | 自动路由已完成。",
    "workflowMode.title": "工作流模式",
    "workflowMode.empty": "当运行首访工作流时，这里会显示“首访准备”或“首访总结”的细分模式。",
    "workflowMode.defaultNotice": "已启用当前模式对应的首访引导。",
    "workflowMode.intake_prep.label": "首访准备",
    "workflowMode.intake_prep.notice": "正在使用访谈前信息收集提纲模式。",
    "workflowMode.initial_interview_summary.label": "首访总结",
    "workflowMode.initial_interview_summary.notice": "正在使用已完成首访材料的固定总结结构。",
    "artifact.downloadWord": "下载可编辑 Word 文档",
    "workspace.export": "备份工作台",
    "workspace.restore": "恢复备份",
    "workspace.refresh": "刷新数据状态",
    "workspace.prune": "清理过期数据",
    "workspace.clear": "清空工作台",
    "workspace.backupLabel": "工作台备份（.zip）",
    "password.loginFirst": "请先登录，再修改工作台密码。",
    "password.fillFields": "请先填写当前密码、新密码和确认密码。",
    "password.updated": "密码已更新。",
    "status.waiting": "等待输入",
  },
  en: {
    "common.none": "None",
    "intro.badge": "Counselor Assistant",
    "intro.title": "Paste counselor material once. Let the workspace route the rest.",
    "intro.body": "The product can prepare initial-interview guides, summarize completed intake notes, organize biopsychosocial case backgrounds, draft session records, build framework-based conceptualizations, and fill Word templates while keeping privacy and review boundaries visible.",
    "intro.roll.w1": "Initial interview",
    "intro.roll.w2": "Case background (BPS)",
    "intro.roll.w3": "Session note drafting",
    "intro.roll.w4": "CBT conceptualization",
    "intro.roll.w5": "Next-session planning",
    "intro.roll.w6": "Counseling roadmap",
    "intro.roll.risk": "Risk boundary reminders",
    "intro.roll.upload": "Word template upload",
    "intro.roll.scan": "Template slot scan",
    "intro.roll.history": "Run history and exports",
    "intro.roll.gov": "Workspace governance",
    "intro.open": "Open workspace",
    "intro.skip": "Skip intro",
    "login.kicker": "Chinese first",
    "login.title": "Counselor workspace sign-in",
    "login.body": "Use de-identified materials for validation first. The default demo credentials can enter now, and you can replace them with formal workspace credentials later.",
    "login.demo.label": "Demo credentials",
    "login.demo.value": "demo / demo123",
    "login.username": "Username",
    "login.usernamePlaceholder": "Enter username",
    "login.password": "Password",
    "login.passwordPlaceholder": "Enter password",
    "login.confirmPassword": "Confirm password",
    "login.confirmPasswordPlaceholder": "Confirm password",
    "login.inviteCode": "Invite code",
    "login.inviteCodePlaceholder": "Enter invite code",
    "login.submit": "Sign in",
    "login.replay": "Replay intro",
    "topbar.brand": "Counselor Assistant",
    "topbar.caption": "Route counselor tasks into structured drafts, notes, exports, and template outputs.",
    "topbar.logout": "Sign out",
    "workflow.AUTO": "Auto detect",
    "workflow.W1": "Initial interview",
    "workflow.W2": "Case background (BPS)",
    "workflow.W3": "Session note",
    "workflow.W4": "Conceptualization",
    "workflow.W5": "Next-session plan",
    "workflow.W6": "Counseling roadmap",
    "workflow.TEMPLATE": "Template draft",
    "auth.mode.login": "Sign in",
    "auth.mode.signup": "Create workspace",
    "auth.hint.loginOnly": "Sign in with your assigned workspace credentials.",
    "auth.hint.loginOrSignup": "Sign in, or create a separate counselor workspace for pilot use.",
    "auth.hint.signupInvite": "Create an isolated counselor workspace with the deployment invite code.",
    "auth.hint.signupOpen": "Create an isolated counselor workspace on this deployment.",
    "auth.pending.login": "Signing in...",
    "auth.pending.signup": "Creating workspace...",
    "auth.signedInAs": "Signed in as {username}",
    "auth.signedOut": "Signed out.",
    "demo.library": "Demo library",
    "demo.signIn": "Sign in to load one-click demos and built-in templates.",
    "demo.scenariosPlaceholder": "De-identified sample workflows will appear here.",
    "demo.templatesPlaceholder": "Bundled Word templates will appear here.",
    "demo.loadedWorkflow": "Loaded {workflow} demo",
    "demo.loadedScenario": "Loaded demo scenario: {title}.",
    "demo.sampleLoaded": "{title}\n\n{summary}\n\nThe sample input has been loaded into the composer. Review it and click Run to start a real model call.",
    "demo.templateLoaded": "Built-in template set to {title}. You can scan slots or start drafting now.",
    "demo.loadSample": "Load sample",
    "demo.useTemplate": "Use template",
    "demo.noneScenario": "No demo scenarios are available in this environment.",
    "demo.noneTemplate": "No bundled Word templates were found.",
    "demo.privacy": "Use de-identified demo material only. Avoid names, phone numbers, IDs, and real client data in public MVP validation.",
    "account.title": "Workspace access",
    "account.signedOut": "Sign in to review the active workspace account and rotate its password when needed.",
    "account.signedIn": "Signed in as {username}. Rotate this workspace password after counselor handoff or any credential change.",
    "governance.title": "Data controls",
    "governance.signedOut": "Review storage, upload limits, and retention before using hosted pilot data.",
    "deployment.title": "Deployment readiness",
    "deployment.signedOut": "Sign in to review model access, workspace auth, retention, and storage durability before pilot launch.",
    "intent.title": "Intent route",
    "intent.empty": "Automatic routing will label the detected counselor task after each run.",
    "intent.routeStatus": "{prefix} | Routing status: {status}.",
    "intent.completed": "{prefix} | Automatic routing completed.",
    "workflowMode.title": "Workflow mode",
    "workflowMode.empty": "W1 prep vs summary details will appear here when the intake workflow runs.",
    "workflowMode.defaultNotice": "Mode-specific intake guidance is active.",
    "workflowMode.intake_prep.label": "Initial interview prep",
    "workflowMode.intake_prep.notice": "Using the pre-interview intake guide mode.",
    "workflowMode.initial_interview_summary.label": "Initial interview summary",
    "workflowMode.initial_interview_summary.notice": "Using the fixed initial interview summary structure for completed intake notes.",
    "artifact.downloadWord": "Download editable Word document",
    "workspace.export": "Backup workspace",
    "workspace.restore": "Restore backup",
    "workspace.refresh": "Refresh data status",
    "workspace.prune": "Prune expired data",
    "workspace.clear": "Clear workspace",
    "workspace.backupLabel": "Workspace backup (.zip)",
    "password.loginFirst": "Sign in before changing the workspace password.",
    "password.fillFields": "Enter the current password and confirm the new password first.",
    "password.updated": "Password updated.",
    "status.waiting": "Waiting for input",
  },
};

function formatMessage(template, params = {}) {
  return String(template || "").replace(/\{(\w+)\}/g, (_match, key) => String(params[key] ?? ""));
}

function t(key, params = {}) {
  const locale = SUPPORTED_LOCALES.includes(state.locale) ? state.locale : DEFAULT_LOCALE;
  const catalog = MESSAGES[locale] || MESSAGES[DEFAULT_LOCALE];
  const fallback = MESSAGES.en || {};
  return formatMessage(catalog[key] || fallback[key] || key, params);
}

function applyLocale(locale = DEFAULT_LOCALE) {
  state.locale = SUPPORTED_LOCALES.includes(locale) ? locale : DEFAULT_LOCALE;
  localStorage.setItem(LOCALE_KEY, state.locale);
  document.documentElement.lang = state.locale;
  document.querySelectorAll("[data-i18n]").forEach((node) => {
    node.textContent = t(node.dataset.i18n);
  });
  document.querySelectorAll("[data-i18n-placeholder]").forEach((node) => {
    node.placeholder = t(node.dataset.i18nPlaceholder);
  });
  $("localeZhButton").classList.toggle("active", state.locale === "zh-CN");
  $("localeEnButton").classList.toggle("active", state.locale === "en");
  updateAuthModeUi();
  initializeWorkspaceBackupUi();
  renderAccountSummary(state.user);
  renderWorkspaceGovernance(null);
  renderDeploymentReadiness(state.deploymentReadiness);
  renderWorkflowModeSummary(state.lastRunData);
  renderIntentSummary(state.lastRunData);
  if (state.demoCatalog) {
    renderDemoCatalog(state.demoCatalog);
  } else {
    clearDemoCatalog();
  }
  const runStatus = $("runStatus");
  if (runStatus && runStatus.classList.contains("idle")) {
    runStatus.textContent = t("status.waiting");
  }
}

function pretty(value) {
  if (value === null || value === undefined || value === "") {
    return t("common.none");
  }
  if (typeof value === "string") {
    return value;
  }
  return JSON.stringify(value, null, 2);
}

function downloadUrl(path) {
  return `/files/${encodeURIComponent(path)}`;
}

function clearNode(node) {
  while (node.firstChild) {
    node.removeChild(node.firstChild);
  }
}

function setPathDisplay(id, path, downloadable = false, downloadLabel = "", downloadHref = "") {
  const target = $(id);
  if (!target) {
    return;
  }
  clearNode(target);
  if (!path) {
    target.textContent = t("common.none");
    return;
  }
  if (!downloadable) {
    target.textContent = path;
    return;
  }
  const link = document.createElement("a");
  link.className = "download-link";
  link.href = downloadHref || downloadUrl(path);
  link.textContent = downloadLabel || path;
  link.download = "";
  target.appendChild(link);
}

function setStatus(text, kind = "idle") {
  const status = $("runStatus");
  status.textContent = text;
  status.className = `status ${kind}`;
}

function setSelectedTemplate(ref, label, message = "") {
  state.selectedTemplateRef = ref || "";
  state.selectedTemplateLabel = label || "";
  if (label) {
    $("templatePath").value = label;
  }
  if (message) {
    $("templatePane").textContent = message;
  }
}

function clearSelectedTemplate() {
  state.selectedTemplateRef = "";
  state.selectedTemplateLabel = "";
}

function syncTemplateSelectionFromInput() {
  if (!state.selectedTemplateRef) {
    return;
  }
  if ($("templatePath").value.trim() !== state.selectedTemplateLabel) {
    clearSelectedTemplate();
  }
}

function setPane(tabName) {
  document.querySelectorAll(".tab").forEach((tab) => {
    const active = tab.dataset.tab === tabName;
    tab.classList.toggle("active", active);
    tab.setAttribute("aria-selected", String(active));
  });

  document.querySelectorAll(".pane").forEach((pane) => pane.classList.remove("active"));
  const paneId =
    tabName === "markdown"
      ? "markdownPane"
      : tabName === "json"
        ? "jsonPane"
        : tabName === "template"
          ? "templatePane"
          : "checksPane";
  $(paneId).classList.add("active");
}

async function postJson(url, payload) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  let data = null;
  try {
    data = await response.json();
  } catch (_error) {
    data = { message: "Response was not valid JSON." };
  }

  if (!response.ok) {
    if (response.status === 401) {
      showLogin();
    }
    throw new Error(data.message || "Request failed.");
  }
  return data;
}

async function getJson(url) {
  const response = await fetch(url);
  const data = await response.json();
  if (!response.ok) {
    if (response.status === 401) {
      showLogin();
    }
    throw new Error(data.message || "Request failed.");
  }
  return data;
}

function applyAuthConfig(config = {}) {
  state.authConfig = {
    signup_enabled: Boolean(config.signup_enabled),
    invite_required: Boolean(config.invite_required),
  };
  $("authModeSignup").hidden = !state.authConfig.signup_enabled;
  if (!state.authConfig.signup_enabled && state.authMode === "signup") {
    state.authMode = "login";
  }
  updateAuthModeUi();
}

function updateAuthModeUi() {
  const signupMode = state.authMode === "signup";
  $("signupConfirmWrap").hidden = !signupMode;
  $("signupInviteWrap").hidden = !signupMode || !state.authConfig.invite_required;
  $("authModeLogin").textContent = t("auth.mode.login");
  $("authModeSignup").textContent = t("auth.mode.signup");
  $("loginSubmitButton").textContent = signupMode ? t("auth.mode.signup") : t("auth.mode.login");
  $("authModeLogin").disabled = !signupMode;
  $("authModeSignup").disabled = signupMode;
  $("authModeHint").textContent = signupMode
    ? state.authConfig.invite_required
      ? t("auth.hint.signupInvite")
      : t("auth.hint.signupOpen")
    : state.authConfig.signup_enabled
      ? t("auth.hint.loginOrSignup")
      : t("auth.hint.loginOnly");
}

function setAuthMode(mode) {
  state.authMode = mode === "signup" ? "signup" : "login";
  updateAuthModeUi();
  $("loginMessage").textContent = "";
}

function showLogin(message = "") {
  $("loginOverlay").classList.remove("hidden");
  $("loginMessage").textContent = message;
  updateAuthModeUi();
}

function hideLogin() {
  $("loginOverlay").classList.add("hidden");
  $("loginMessage").textContent = "";
}

function showIntro() {
  $("introOverlay").classList.remove("hidden");
  $("loginOverlay").classList.add("hidden");
}

function hideIntro() {
  $("introOverlay").classList.add("hidden");
}

function completeIntro() {
  localStorage.setItem(INTRO_KEY, "1");
  hideIntro();
  showLogin();
}

function shouldShowIntro() {
  if (new URLSearchParams(window.location.search).get("intro") === "1") {
    return true;
  }
  return localStorage.getItem(INTRO_KEY) !== "1";
}

function workspace() {
  return document.querySelector(".workspace");
}

function setSideCollapsed(collapsed) {
  workspace().classList.toggle("side-collapsed", collapsed);
  localStorage.setItem(SIDE_COLLAPSED_KEY, collapsed ? "1" : "0");
}

function applySavedSidePanelState() {
  const savedWidth = Number(localStorage.getItem(SIDE_WIDTH_KEY));
  if (savedWidth >= 220 && savedWidth <= 420) {
    document.documentElement.style.setProperty("--side-width", `${savedWidth}px`);
  }
  setSideCollapsed(localStorage.getItem(SIDE_COLLAPSED_KEY) === "1");
}

function beginSideResize(event) {
  if (workspace().classList.contains("side-collapsed")) {
    return;
  }
  event.preventDefault();
  const startX = event.clientX;
  const currentWidth = document.querySelector(".side-panel").getBoundingClientRect().width;
  workspace().classList.add("resizing");

  function move(pointerEvent) {
    const nextWidth = Math.min(420, Math.max(220, currentWidth + pointerEvent.clientX - startX));
    document.documentElement.style.setProperty("--side-width", `${nextWidth}px`);
    localStorage.setItem(SIDE_WIDTH_KEY, String(Math.round(nextWidth)));
  }

  function stop() {
    workspace().classList.remove("resizing");
    window.removeEventListener("pointermove", move);
    window.removeEventListener("pointerup", stop);
  }

  window.addEventListener("pointermove", move);
  window.addEventListener("pointerup", stop);
}

function selectedCaseId() {
  return $("caseSelect").value || "";
}

function selectedCaseTitle() {
  return state.caseDetail && state.caseDetail.case ? state.caseDetail.case.title : "";
}

function selectedClientCode() {
  return state.caseDetail && state.caseDetail.case ? state.caseDetail.case.client_code || "" : "";
}

function canFillFromStructured() {
  return Boolean(state.runDir && state.structuredOutput);
}

function updateTemplateAvailability() {
  $("fillTemplateButton").disabled = !canFillFromStructured();
}

function formatTimestamp(value) {
  if (!value) {
    return "Unknown time";
  }
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString("zh-CN", { hour12: false });
}

function formatBytes(value) {
  const bytes = Number(value || 0);
  if (!Number.isFinite(bytes) || bytes <= 0) {
    return "0 B";
  }
  if (bytes < 1024) {
    return `${bytes} B`;
  }
  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`;
  }
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function addStackPlaceholder(id, text) {
  const container = $(id);
  clearNode(container);
  const item = document.createElement("div");
  item.className = "stack-item";
  const label = document.createElement("span");
  label.textContent = text;
  item.appendChild(label);
  container.appendChild(item);
}

function createDownloadLink(path, label) {
  const link = document.createElement("a");
  link.className = "download-link";
  link.href = downloadUrl(path);
  link.textContent = label;
  link.download = "";
  return link;
}

function createActionButton(label, onClick) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "link-button";
  button.textContent = label;
  button.addEventListener("click", onClick);
  return button;
}

function createMiniGhostButton(label, onClick) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "ghost-button mini-button";
  button.textContent = label;
  button.addEventListener("click", onClick);
  return button;
}

function workflowLabel(workflow) {
  return t(`workflow.${workflow || "AUTO"}`);
}

function ensureDeleteCaseButton() {
  let button = $("deleteCaseButton");
  if (button) {
    return button;
  }
  const exportButton = $("exportCaseButton");
  if (!exportButton) {
    return null;
  }
  button = document.createElement("button");
  button.id = "deleteCaseButton";
  button.type = "button";
  button.className = "ghost-button wide danger-button";
  button.textContent = "Delete case";
  exportButton.insertAdjacentElement("afterend", button);
  return button;
}

function updateCaseActions() {
  const hasCase = Boolean(selectedCaseId());
  $("saveCaseButton").disabled = !hasCase;
  $("exportCaseButton").disabled = !hasCase;
  const deleteButton = ensureDeleteCaseButton();
  if (deleteButton) {
    deleteButton.disabled = !hasCase;
  }
}

function clearDemoCatalog(message = "") {
  state.demoCatalog = null;
  $("demoCatalogStatus").innerHTML = `<strong>${t("demo.library")}</strong><span>${message || t("demo.signIn")}</span>`;
  addStackPlaceholder("demoStarterList", t("demo.scenariosPlaceholder"));
  addStackPlaceholder("demoTemplateList", t("demo.templatesPlaceholder"));
}

function applyDemoTemplate(templateRef, title = "template") {
  setSelectedTemplate(
    templateRef,
    title,
    t("demo.templateLoaded", { title }),
  );
  $("auditStatus").textContent = t("demo.templateLoaded", { title });
  setPane("template");
}

function applyDemoScenario(scenarioId) {
  const scenario = (state.demoCatalog && state.demoCatalog.scenarios || []).find((item) => item.id === scenarioId);
  if (!scenario) {
    return;
  }
  $("inputText").value = scenario.input || "";
  $("outputStyleSelect").value = scenario.output_style || "default";
  $("outputCustomStyle").value = "";
  $("markdownPane").textContent = t("demo.sampleLoaded", {
    title: scenario.title,
    summary: scenario.summary,
  });
  setStatus(t("demo.loadedWorkflow", { workflow: workflowLabel(scenario.workflow) }), "idle");
  $("auditStatus").textContent = t("demo.loadedScenario", { title: scenario.title });
  setPane("markdown");
}

function renderDemoCatalog(payload) {
  state.demoCatalog = payload;
  $("demoCatalogStatus").innerHTML = `<strong>${t("demo.library")}</strong><span>${payload.privacy_notice || t("demo.privacy")}</span>`;

  const starterList = $("demoStarterList");
  clearNode(starterList);
  (payload.scenarios || []).forEach((scenario) => {
    const card = document.createElement("div");
    card.className = "demo-card";
    const title = document.createElement("strong");
    title.textContent = scenario.title;
    const summary = document.createElement("span");
    summary.textContent = `${workflowLabel(scenario.workflow)} | ${scenario.summary}`;
    const actions = document.createElement("div");
    actions.className = "button-row";
    actions.appendChild(createMiniGhostButton(t("demo.loadSample"), () => applyDemoScenario(scenario.id)));
    card.append(title, summary, actions);
    starterList.appendChild(card);
  });
  if (!starterList.children.length) {
    addStackPlaceholder("demoStarterList", t("demo.noneScenario"));
  }

  const templateList = $("demoTemplateList");
  clearNode(templateList);
  (payload.templates || []).forEach((template) => {
    const card = document.createElement("div");
    card.className = "demo-card";
    const title = document.createElement("strong");
    title.textContent = template.title;
    const summary = document.createElement("span");
    summary.textContent = template.summary || template.title;
    const actions = document.createElement("div");
    actions.className = "button-row";
    actions.appendChild(createMiniGhostButton(t("demo.useTemplate"), () => applyDemoTemplate(template.template_ref, template.title)));
    card.append(title, summary, actions);
    templateList.appendChild(card);
  });
  if (!templateList.children.length) {
    addStackPlaceholder("demoTemplateList", t("demo.noneTemplate"));
  }
}

async function loadDemoCatalog() {
  try {
    const payload = await postJson("/api/cases", { action: "demo_catalog" });
    if (Array.isArray(payload.scenarios) && payload.scenarios.length) {
      renderDemoCatalog(payload);
      return;
    }
    renderDemoCatalog({ ...FALLBACK_DEMO_CATALOG, templates: payload.templates || [] });
  } catch (error) {
    renderDemoCatalog(FALLBACK_DEMO_CATALOG);
  }
}

function actionLabel(action) {
  return {
    "workflow.run": "Workflow run",
    "template.draft": "Template draft",
    "file.upload": "File upload",
    "case.create": "Case created",
    "case.update": "Case updated",
    "case.export": "Case export",
    "workspace.export": "Workspace backup",
    "workspace.restore": "Workspace restore",
  }[action] || action;
}

function formatTemplateSummary(data) {
  const summary = data.summary || {};
  const slots = data.slots || [];
  const typeText = Object.entries(summary.slot_types || {})
    .map(([type, count]) => `${type}: ${count}`)
    .join(", ") || "None";
  const preview = slots
    .slice(0, 30)
    .map((slot, index) => {
      const current = slot.current_text && slot.current_text !== slot.label ? ` current: ${slot.current_text}` : "";
      return `${index + 1}. ${slot.label || "Unnamed slot"} (${slot.slot_type})${current}`;
    })
    .join("\n");
  const more = slots.length > 30 ? `\n... ${slots.length - 30} more slots not shown` : "";
  return [
    `Detected slots: ${summary.total_slots || 0}`,
    `Fillable slots: ${summary.fillable_slots || 0}`,
    `Prefilled slots: ${summary.prefilled_slots || 0}`,
    `Slot types: ${typeText}`,
    "",
    preview || "No fillable slots were detected in this template.",
    more,
  ].join("\n");
}

function formatReportSummary(report) {
  if (!report || typeof report !== "object") {
    return pretty(report);
  }
  const filled = report.filled_fields || [];
  const drafted = report.drafted_fields || [];
  const kept = report.kept_fields || [];
  const skipped = report.skipped_fields || [];
  const unfilled = report.unfilled_fields || [];
  const issues = report.issues || [];
  const lines = [
    `Status: ${report.status || "Unknown"}`,
    `Filled fields: ${filled.length}`,
    `Drafted fields: ${drafted.length}`,
    `Kept fields: ${kept.length}`,
    `Skipped fields: ${skipped.length}`,
    `Unfilled fields: ${unfilled.length}`,
    `Issues: ${issues.length}`,
  ];
  const important = [...unfilled, ...skipped, ...issues].slice(0, 12);
  if (important.length) {
    lines.push("", "Needs review:");
    important.forEach((item, index) => {
      const label = item.template_label || item.location || item.slot_id || "Unnamed item";
      const reason = item.reason || item.message || "No reason provided";
      lines.push(`${index + 1}. ${label}: ${reason}`);
    });
  }
  lines.push("", "Full report:", pretty(report));
  return lines.join("\n");
}

function renderCaseExportSummary(data) {
  const box = $("caseExportSummary");
  box.innerHTML = "";
  const title = document.createElement("strong");
  title.textContent = "Case export";
  const body = document.createElement("span");
  if (!data || !data.output_path) {
    body.textContent = "Select a case to bundle its notes, uploads, recent runs, and generated outputs.";
    box.append(title, body);
    return;
  }
  const manifest = data.manifest || {};
  const artifacts = manifest.artifacts || {};
  body.textContent = `Includes ${artifacts.run_count || 0} runs, ${artifacts.upload_count || 0} uploads, and ${artifacts.audit_log_count || 0} audit entries.`;
  box.append(title, body, createDownloadLink(data.output_path, "Download bundle"));
}

function renderWorkspaceBackupSummary(data) {
  const box = $("workspaceBackupSummary");
  if (!box) {
    return;
  }
  box.innerHTML = "";
  const title = document.createElement("strong");
  title.textContent = "Workspace backup";
  const body = document.createElement("span");
  if (!data || !data.output_path) {
    body.textContent = "Download a full snapshot of this account's cases, uploads, run folders, and activity for restore on a fresh instance.";
    box.append(title, body);
    return;
  }
  const counts = (data.manifest && data.manifest.counts) || {};
  body.textContent = `Includes ${counts.cases || 0} cases, ${counts.uploads || 0} uploads, and ${counts.runs || 0} run folders.`;
  box.append(title, body, createDownloadLink(data.output_path, "Download backup"));
}

function renderAccountSummary(user = state.user) {
  const box = $("accountSummary");
  if (!box) {
    return;
  }
  box.innerHTML = "";
  const title = document.createElement("strong");
  title.textContent = t("account.title");
  const body = document.createElement("span");
  if (!user) {
    body.textContent = t("account.signedOut");
    box.append(title, body);
    return;
  }
  body.textContent = t("account.signedIn", { username: user.username });
  box.append(title, body);
}

function renderWorkspaceGovernance(data) {
  const box = $("workspaceGovernanceSummary");
  if (!box) {
    return;
  }
  const activeData = data || state.workspaceGovernance;
  const policy = (activeData && activeData.policy) || state.workspacePolicy || {};
  if (data && data.policy) {
    state.workspacePolicy = data.policy;
  }
  if (data) {
    state.workspaceGovernance = data;
  }
  const summary = (activeData && activeData.summary) || null;
  box.innerHTML = "";
  const title = document.createElement("strong");
  title.textContent = t("governance.title");
  const body = document.createElement("span");
  if (!summary) {
    body.textContent = t("governance.signedOut");
    box.append(title, body);
    return;
  }
  const counts = summary.counts || {};
  const storage = summary.storage || {};
  const retentionLabel = policy.retention_days ? `${policy.retention_days} days` : "Manual only";
  body.textContent =
    `${counts.cases || 0} cases, ${counts.uploads || 0} uploads, ${counts.run_artifacts || 0} saved runs, ` +
    `${formatBytes(storage.total_bytes || 0)} total. Upload cap ${formatBytes(policy.max_upload_bytes || 0)}, retention ${retentionLabel}.`;
  box.append(title, body);
}

function renderDeploymentReadiness(readiness) {
  const box = $("deploymentReadinessSummary");
  if (!box) {
    return;
  }
  box.innerHTML = "";
  const title = document.createElement("strong");
  title.textContent = t("deployment.title");
  const body = document.createElement("span");
  const activeReadiness = readiness || state.deploymentReadiness;
  if (!activeReadiness) {
    body.textContent = t("deployment.signedOut");
    box.append(title, body);
    return;
  }
  state.deploymentReadiness = activeReadiness;
  const summary = activeReadiness.summary || {};
  const checks = activeReadiness.checks || [];
  const statusPrefix = activeReadiness.pilot_ready
    ? `Pilot-ready with ${summary.warn_count || 0} warning(s).`
    : `${summary.fail_count || 0} blocking issue(s), ${summary.warn_count || 0} warning(s).`;
  const notable = checks
    .filter((item) => item.status !== "pass")
    .slice(0, 2)
    .map((item) => item.detail)
    .join(" ");
  body.textContent = notable ? `${statusPrefix} ${notable}` : statusPrefix;
  box.append(title, body);
}

function renderIntentSummary(data) {
  const box = $("intentSummary");
  if (!box) {
    return;
  }
  const detected = data && (data.detected_workflow || data.workflow || "AUTO");
  const routeStatus = data && data.route_status;
  const routeNotice = data && data.route_notice;
  const routeReasonsSummary = data && data.routing_reasons_summary;
  const title = document.createElement("strong");
  title.textContent = t("intent.title");
  const body = document.createElement("span");
  const prefix = workflowLabel(detected);
  if (!data) {
    body.textContent = t("intent.empty");
  } else if (routeNotice) {
    body.textContent = routeReasonsSummary
      ? `${prefix} | ${routeNotice} ${routeReasonsSummary}`
      : `${prefix} | ${routeNotice}`;
  } else if (routeStatus) {
    body.textContent = t("intent.routeStatus", { prefix, status: routeStatus });
  } else {
    body.textContent = t("intent.completed", { prefix });
  }
  box.innerHTML = "";
  box.append(title, body);
}

function renderWorkflowModeSummary(data) {
  const box = $("workflowModeSummary");
  if (!box) {
    return;
  }
  const title = document.createElement("strong");
  title.textContent = t("workflowMode.title");
  const body = document.createElement("span");
  if (!data || !data.workflow_mode_label) {
    body.textContent = t("workflowMode.empty");
  } else {
    const modeLabel = t(`workflowMode.${data.workflow_mode}.label`);
    const modeNotice = t(`workflowMode.${data.workflow_mode}.notice`);
    body.textContent = `${modeLabel} | ${modeNotice || data.workflow_mode_notice || t("workflowMode.defaultNotice")}`;
  }
  box.innerHTML = "";
  box.append(title, body);
}

function renderW1SummaryBrief(data) {
  const box = $("w1SummaryBrief");
  if (!box) {
    return;
  }
  const title = document.createElement("strong");
  title.textContent = "W1 summary brief";
  const body = document.createElement("span");
  const brief = data && data.w1_summary_brief;
  if (!brief) {
    body.textContent = "Completed initial interview highlights will appear here after a W1 summary run.";
  } else {
    const parts = [];
    if (brief.main_distress) {
      parts.push(`Main distress: ${brief.main_distress}`);
    }
    if (brief.risk_highlight) {
      parts.push(`Risk highlight: ${brief.risk_highlight}`);
    }
    if (brief.follow_up_priority) {
      parts.push(`Priority follow-up: ${brief.follow_up_priority}`);
    }
    if (brief.biggest_gap) {
      parts.push(`Biggest gap: ${brief.biggest_gap}`);
    }
    body.textContent = parts.join(" | ") || "Completed initial interview highlights will appear here after a W1 summary run.";
  }
  box.innerHTML = "";
  box.append(title, body);
}

function renderW3RecordBrief(data) {
  const box = $("w3RecordBrief");
  if (!box) {
    return;
  }
  const title = document.createElement("strong");
  title.textContent = "W3 record brief";
  const body = document.createElement("span");
  const brief = data && data.w3_record_brief;
  if (!brief) {
    body.textContent = "Session-record highlights will appear here after a W3 counseling-record run.";
  } else {
    const parts = [];
    if (brief.record_format) {
      parts.push(`Format: ${brief.record_format}`);
    }
    if (brief.behavior_highlight) {
      parts.push(`Behavior/data: ${brief.behavior_highlight}`);
    }
    if (brief.intervention_highlight) {
      parts.push(`Intervention: ${brief.intervention_highlight}`);
    }
    if (brief.risk_highlight) {
      parts.push(`Risk highlight: ${brief.risk_highlight}`);
    }
    if (brief.next_focus) {
      parts.push(`Next focus: ${brief.next_focus}`);
    }
    body.textContent = parts.join(" | ") || "Session-record highlights will appear here after a W3 counseling-record run.";
  }
  box.innerHTML = "";
  box.append(title, body);
}

function updateRunResult(data) {
  state.lastRunData = data || null;
  state.runDir = data.run_dir || null;
  state.structuredOutput = data.structured_output || null;

  $("markdownPane").textContent = data.clean_output || data.raw_output || "No model output returned.";
  $("jsonPane").textContent = pretty(data.structured_output);
  $("checksPane").textContent = pretty({
    structured_check: data.structured_check,
    safety_check: data.safety_check,
    metadata: data.metadata,
    docx: data.docx,
    issues: data.issues,
  });
  $("intentDisplay").textContent = workflowLabel(data.detected_workflow || data.workflow || "AUTO");
  setPathDisplay("runDir", data.run_dir, false);
  setPathDisplay(
    "docxPath",
    data.docx && data.docx.path ? data.docx.path : null,
    true,
    data.docx && data.docx.filename
      ? `${t("artifact.downloadWord")} (${data.docx.filename})`
      : t("artifact.downloadWord"),
    data.docx && data.docx.download_url ? data.docx.download_url : "",
  );
  renderIntentSummary(data);
  renderWorkflowModeSummary(data);
  renderW1SummaryBrief(data);
  renderW3RecordBrief(data);
  updateTemplateAvailability();
}

function renderCaseUploads(uploads) {
  const summary = $("caseUploadsSummary");
  const list = $("caseUploadsList");
  clearNode(list);
  if (!uploads.length) {
    summary.innerHTML = "<strong>Linked files</strong><span>No files are attached to this case yet.</span>";
    addStackPlaceholder("caseUploadsList", "Uploaded Word templates and materials will appear here.");
    return;
  }

  summary.innerHTML = `<strong>Linked files</strong><span>This case has ${uploads.length} uploaded file(s) ready for reuse in the template workflow.</span>`;
  uploads.forEach((upload) => {
    const item = document.createElement("div");
    item.className = "stack-item";
    const title = document.createElement("strong");
    title.textContent = upload.original_name;
    const meta = document.createElement("span");
    const sizeKb = Math.max(1, Math.round((upload.size_bytes || 0) / 1024));
    meta.textContent = `${formatTimestamp(upload.created_at)} 路 ${sizeKb} KB`;
    item.append(title, meta);
    item.appendChild(createDownloadLink(upload.stored_path, "Download"));
    item.appendChild(
      createActionButton("Use as template", () => {
        setSelectedTemplate(
          upload.template_ref || "",
          upload.original_name,
          `Current template set to ${upload.original_name}.`,
        );
        setPathDisplay("uploadedTemplatePath", upload.stored_path, false);
        setPane("template");
      }),
    );
    list.appendChild(item);
  });
}

function renderCaseActivity(entries) {
  const list = $("caseActivityList");
  clearNode(list);
  if (!entries.length) {
    addStackPlaceholder("caseActivityList", "Runs, template actions, and uploads will appear here in reverse chronological order.");
    return;
  }

  entries.forEach((entry) => {
    const item = document.createElement("div");
    item.className = "stack-item";
    const title = document.createElement("strong");
    title.textContent = actionLabel(entry.action);
    const meta = document.createElement("time");
    meta.textContent = formatTimestamp(entry.timestamp || entry.created_at);
    const detail = document.createElement("span");
    const details = entry.details || {};
    detail.textContent =
      details.workflow
        ? `${workflowLabel(details.workflow)} | ${details.status || "Completed"}`
        : details.original_name
          ? `File: ${details.original_name}`
          : details.title || "Recent activity";
    item.append(title, meta, detail);
    if (details.run_dir) {
      item.appendChild(createActionButton("Open result", () => openSavedRun(details.run_dir)));
    }
    if (details.output_path) {
      item.appendChild(createDownloadLink(details.output_path, "Download output"));
    } else if (details.stored_path) {
      item.appendChild(createDownloadLink(details.stored_path, "Download file"));
    } else if (details.run_dir) {
      const runDir = document.createElement("span");
      runDir.textContent = `Run: ${details.run_dir}`;
      item.appendChild(runDir);
    }
    list.appendChild(item);
  });
}

function ensureSavedRunsSection() {
  if ($("runArtifactList")) {
    return $("runArtifactList");
  }
  const activitySection = $("caseActivityList") && $("caseActivityList").closest(".soft-section");
  if (!activitySection || !activitySection.parentNode) {
    return null;
  }
  const section = document.createElement("div");
  section.className = "soft-section";
  section.innerHTML = [
    '<div class="section-title">',
    "<strong>Saved runs</strong>",
    "<span>Reopen prior outputs, JSON checks, and generated Word files for this case.</span>",
    "</div>",
    '<div id="runArtifactList" class="stack-list muted-list"></div>',
  ].join("");
  activitySection.parentNode.insertBefore(section, activitySection);
  return $("runArtifactList");
}

function renderSavedRuns(runs) {
  const list = ensureSavedRunsSection();
  if (!list) {
    return;
  }
  clearNode(list);
  if (!runs.length) {
    addStackPlaceholder("runArtifactList", "Saved workflow and template runs will appear here for reopening.");
    return;
  }

  runs.forEach((run) => {
    const item = document.createElement("div");
    item.className = "stack-item";
    const title = document.createElement("strong");
    title.textContent = `${workflowLabel(run.workflow)} | ${run.run_name || "saved run"}`;
    const meta = document.createElement("span");
    const fileCount = Array.isArray(run.available_files) ? run.available_files.length : 0;
    meta.textContent = `${formatTimestamp(run.created_at)} | ${fileCount} artifact(s)`;
    item.append(title, meta);
    item.appendChild(createActionButton("Open result", () => openSavedRun(run.run_dir)));
    if (run.download_files && run.download_files.docx) {
      item.appendChild(createDownloadLink(run.download_files.docx, "Download Word"));
    }
    list.appendChild(item);
  });
}

function renderCaseDetail(payload) {
  state.caseDetail = payload;
  const caseRecord = payload.case;
  $("caseNotesInput").value = caseRecord.notes || "";
  $("caseSummary").innerHTML = "";
  const title = document.createElement("strong");
  title.textContent = caseRecord.title;
  const body = document.createElement("span");
  body.textContent = caseRecord.client_code
    ? `Code ${caseRecord.client_code} | ${payload.uploads.length} files | ${payload.recent_runs.length} recent items`
    : `${payload.uploads.length} files | ${payload.recent_runs.length} recent items`;
  $("caseSummary").append(title, body);
  renderCaseUploads(payload.uploads || []);
  renderSavedRuns(payload.run_artifacts || []);
  renderCaseActivity(payload.recent_runs || []);
  updateCaseActions();
}

function clearCaseDetail() {
  state.caseDetail = null;
  $("caseNotesInput").value = "";
  $("caseSummary").innerHTML = "<strong>Current case</strong><span>No case selected.</span>";
  $("caseUploadsSummary").innerHTML = "<strong>Linked files</strong><span>Select a case to view its uploaded templates and source materials.</span>";
  renderCaseExportSummary(null);
  renderWorkspaceBackupSummary(null);
  addStackPlaceholder("caseUploadsList", "Uploaded Word templates and materials will appear here.");
  ensureSavedRunsSection();
  addStackPlaceholder("runArtifactList", "Saved workflow and template runs will appear here for reopening.");
  addStackPlaceholder("caseActivityList", "Runs, template actions, and uploads will appear here in reverse chronological order.");
  updateCaseActions();
}

function showRunError(message) {
  $("checksPane").textContent = message;
  setPane("checks");
}

function updateTemplateResult(data) {
  if (data.run_dir) {
    state.runDir = data.run_dir;
    setPathDisplay("runDir", data.run_dir, false);
  }
  setPathDisplay("filledTemplatePath", data.output_path, true);
  setPathDisplay("templateDraftPath", data.draft_path, true);
  setPathDisplay("templateMappingPath", data.mapping_path, true);
  setPathDisplay("templateReportPath", data.report_path, true);
  $("templatePane").textContent = formatReportSummary(data.report);
  setPane("template");
  updateTemplateAvailability();
}

function templatePayloadBase() {
  syncTemplateSelectionFromInput();
  return {
    template_path: $("templatePath").value.trim(),
    template_ref: state.selectedTemplateRef || undefined,
    llm_map: $("templateLlmMapToggle").checked,
  };
}

async function runAgent() {
  const input = $("inputText").value.trim();
  if (!input) {
    setStatus("Missing input", "error");
    showRunError("Enter counselor material before running a workflow.");
    return;
  }

  setStatus("Running", "running");
  $("runButton").disabled = true;

  try {
    const data = await postJson("/api/run", {
      workflow: state.workflow,
      input,
      structured: $("structuredToggle").checked,
      render_docx: $("docxToggle").checked,
      dry_run: $("dryRunToggle").checked,
      output_style: $("outputStyleSelect").value,
      custom_output_style: $("outputCustomStyle").value.trim(),
      case_id: selectedCaseId(),
    });
    updateRunResult(data);
    if (selectedCaseId()) {
      await loadCaseDetail(selectedCaseId());
    }
    setStatus(data.status === "success" ? "Success" : data.status || "Complete", data.status === "error" ? "error" : "success");
  } catch (error) {
    state.runDir = null;
    state.structuredOutput = null;
    updateTemplateAvailability();
    setStatus("Failed", "error");
    showRunError(error.message);
  } finally {
    $("runButton").disabled = false;
  }
}

async function draftTemplate() {
  const templatePath = $("templatePath").value.trim();
  const rawInput = $("inputText").value.trim();
  if (!templatePath) {
    $("templatePane").textContent = "Enter a Word template path or upload a .docx template first.";
    setPane("template");
    return;
  }
  if (!rawInput) {
    $("templatePane").textContent = "Enter counselor material before drafting the template.";
    setPane("template");
    return;
  }

  $("draftTemplateButton").disabled = true;
  $("fillTemplateButton").disabled = true;
  $("templatePane").textContent = "Understanding the template and drafting slot content...";
  setPane("template");

  try {
    const data = await postJson("/api/draft-template", {
      ...templatePayloadBase(),
      raw_input: rawInput,
      style: $("styleSelect").value,
      custom_style: $("customStyle").value.trim(),
      existing_content_policy: $("existingPolicy").value,
      run_dir: state.runDir,
      case_id: selectedCaseId(),
    });
    updateTemplateResult(data);
    if (selectedCaseId()) {
      await loadCaseDetail(selectedCaseId());
    }
  } catch (error) {
    $("templatePane").textContent = error.message;
    setPane("template");
  } finally {
    $("draftTemplateButton").disabled = false;
    updateTemplateAvailability();
  }
}

async function inspectTemplate() {
  const templatePath = $("templatePath").value.trim();
  if (!templatePath) {
    $("templateSummary").innerHTML = "<strong>Template scan</strong><span>Enter a Word template path or upload a .docx file first.</span>";
    $("templatePane").textContent = "Enter a Word template path or upload a .docx file first.";
    setPane("template");
    return;
  }

  $("inspectTemplateButton").disabled = true;
  $("templateSummary").innerHTML = "<strong>Template scan</strong><span>Scanning template slots...</span>";
  $("templatePane").textContent = "Scanning template slots...";
  setPane("template");

  try {
    const data = await postJson("/api/inspect-template", templatePayloadBase());
    state.templateSlots = data.slots || [];
    $("templateSummary").innerHTML = "";
    const title = document.createElement("strong");
    title.textContent = "Template scan";
    const body = document.createElement("span");
    body.textContent = formatTemplateSummary(data);
    $("templateSummary").append(title, body);
    $("templatePane").textContent = formatTemplateSummary(data);
  } catch (error) {
    state.templateSlots = [];
    $("templateSummary").innerHTML = "";
    const title = document.createElement("strong");
    title.textContent = "Template scan failed";
    const body = document.createElement("span");
    body.textContent = error.message;
    $("templateSummary").append(title, body);
    $("templatePane").textContent = error.message;
  } finally {
    $("inspectTemplateButton").disabled = false;
  }
}

async function fillTemplateFromStructured() {
  const templatePath = $("templatePath").value.trim();
  if (!canFillFromStructured()) {
    $("templatePane").textContent = "Run a workflow with structured output first, or use intelligent template drafting above.";
    setPane("template");
    return;
  }
  if (!templatePath) {
    $("templatePane").textContent = "Enter a Word template path or upload a .docx template first.";
    setPane("template");
    return;
  }

  $("fillTemplateButton").disabled = true;
  $("templatePane").textContent = "Filling the template from structured JSON...";
  setPane("template");

  try {
    const data = await postJson("/api/fill-template", {
      run_dir: state.runDir,
      ...templatePayloadBase(),
    });
    updateTemplateResult(data);
    if (selectedCaseId()) {
      await loadCaseDetail(selectedCaseId());
    }
  } catch (error) {
    $("templatePane").textContent = error.message;
    setPane("template");
  } finally {
    updateTemplateAvailability();
  }
}

async function openSavedRun(runDir) {
  if (!runDir) {
    return;
  }
  setStatus("Loading saved run", "running");
  try {
    const data = await postJson("/api/runs", {
      action: "detail",
      run_dir: runDir,
    });
    updateRunResult(data);
    $("auditStatus").textContent = `Loaded saved run ${data.run_name || ""}`.trim();
    setStatus(`Loaded ${workflowLabel(data.workflow)}`, "success");
    setPane("markdown");
  } catch (error) {
    setStatus("Failed", "error");
    showRunError(error.message);
  }
}

async function submitAuthForm(event) {
  event.preventDefault();
  const signupMode = state.authMode === "signup";
  $("loginMessage").textContent = signupMode ? t("auth.pending.signup") : t("auth.pending.login");
  try {
    const data = await postJson(signupMode ? "/api/signup" : "/api/login", {
      username: $("loginUsername").value.trim(),
      password: $("loginPassword").value,
      password_confirm: $("signupPasswordConfirm").value,
      invite_code: $("signupInviteCode").value.trim(),
    });
    state.user = data.user;
    applyAuthConfig(data.auth_config || state.authConfig);
    state.workspacePolicy = data.workspace_policy || state.workspacePolicy;
    state.deploymentReadiness = data.deployment_readiness || state.deploymentReadiness;
    renderDeploymentReadiness(state.deploymentReadiness);
    renderAccountSummary(state.user);
    localStorage.setItem(LOGIN_USERNAME_KEY, data.user.username);
    hideLogin();
    await Promise.all([loadCases(), loadDemoCatalog(), refreshWorkspaceGovernance()]);
    $("auditStatus").textContent = t("auth.signedInAs", { username: data.user.username });
  } catch (error) {
    $("loginMessage").textContent = error.message;
  }
}

function primeLoginForm() {
  $("loginUsername").value = localStorage.getItem(LOGIN_USERNAME_KEY) || "";
  $("loginPassword").value = "";
  $("signupPasswordConfirm").value = "";
  $("signupInviteCode").value = "";
  setAuthMode("login");
}

async function logout() {
  await postJson("/api/logout", {});
  state.user = null;
  state.caseId = "";
  state.lastRunData = null;
  state.workspaceGovernance = null;
  state.deploymentReadiness = null;
  $("caseSelect").innerHTML = '<option value="">No case selected</option>';
  clearCaseDetail();
  clearDemoCatalog();
  renderAccountSummary(null);
  renderWorkspaceGovernance(null);
  renderDeploymentReadiness(null);
  showLogin(t("auth.signedOut"));
}

async function checkSession() {
  try {
    if (shouldShowIntro()) {
      showIntro();
      return;
    }
    const data = await getJson("/api/session");
    applyAuthConfig(data.auth_config || {});
    state.workspacePolicy = data.workspace_policy || state.workspacePolicy;
    state.deploymentReadiness = data.deployment_readiness || null;
    renderDeploymentReadiness(state.deploymentReadiness);
    if (data.authenticated) {
      state.user = data.user;
      renderAccountSummary(state.user);
      hideLogin();
      await Promise.all([loadCases(), loadDemoCatalog(), refreshWorkspaceGovernance()]);
      $("auditStatus").textContent = t("auth.signedInAs", { username: data.user.username });
    } else {
      renderAccountSummary(null);
      clearDemoCatalog();
      renderWorkspaceGovernance(null);
      showLogin();
    }
  } catch (error) {
    renderAccountSummary(null);
    clearDemoCatalog();
    renderWorkspaceGovernance(null);
    renderDeploymentReadiness(null);
    showLogin(error.message);
  }
}

function renderCases(cases) {
  const select = $("caseSelect");
  const current = select.value;
  select.innerHTML = '<option value="">No case selected</option>';
  cases.forEach((caseItem) => {
    const option = document.createElement("option");
    option.value = String(caseItem.id);
    option.textContent = caseItem.client_code ? `${caseItem.title} (${caseItem.client_code})` : caseItem.title;
    select.appendChild(option);
  });
  if ([...select.options].some((option) => option.value === current)) {
    select.value = current;
  }
  state.caseId = select.value;
  updateCaseActions();
}

async function loadCases() {
  const data = await postJson("/api/cases", {});
  renderCases(data.cases || []);
  if (state.caseId) {
    await loadCaseDetail(state.caseId);
  } else {
    clearCaseDetail();
  }
}

async function loadCaseDetail(caseId = selectedCaseId()) {
  if (!caseId) {
    clearCaseDetail();
    return;
  }
  const data = await postJson("/api/cases", {
    action: "detail",
    case_id: caseId,
  });
  renderCaseDetail(data);
}

async function createCase() {
  const title = $("caseTitleInput").value.trim();
  if (!title) {
    $("auditStatus").textContent = "Enter a case title first.";
    return;
  }
  const data = await postJson("/api/cases", {
    action: "create",
    title,
    client_code: $("clientCodeInput").value.trim(),
  });
  await loadCases();
  $("caseSelect").value = String(data.case.id);
  state.caseId = String(data.case.id);
  await loadCaseDetail(state.caseId);
  $("caseTitleInput").value = "";
  $("clientCodeInput").value = "";
  $("auditStatus").textContent = "Case created.";
}

async function saveCaseNotes() {
  const caseId = selectedCaseId();
  if (!caseId) {
    $("auditStatus").textContent = "Select a case before saving notes.";
    return;
  }
  const payload = await postJson("/api/cases", {
    action: "update",
    case_id: caseId,
    title: selectedCaseTitle(),
    client_code: selectedClientCode(),
    notes: $("caseNotesInput").value.trim(),
  });
  await loadCaseDetail(caseId);
  $("auditStatus").textContent = `Saved case notes for ${payload.case.title}.`;
}

async function exportCasePackage() {
  const caseId = selectedCaseId();
  if (!caseId) {
    $("auditStatus").textContent = "Select a case before exporting a bundle.";
    return;
  }
  $("exportCaseButton").disabled = true;
  $("checksPane").textContent = "Building case bundle...";
  setPane("checks");
  try {
    const payload = await postJson("/api/cases", {
      action: "export",
      case_id: caseId,
    });
    renderCaseExportSummary(payload);
    $("checksPane").textContent = pretty(payload.manifest || payload);
    if (selectedCaseId()) {
      await loadCaseDetail(selectedCaseId());
    }
    $("auditStatus").textContent = "Case bundle generated.";
  } catch (error) {
    $("checksPane").textContent = error.message;
    $("auditStatus").textContent = error.message;
    setPane("checks");
  } finally {
    $("exportCaseButton").disabled = false;
  }
}

async function deleteCase() {
  const caseId = selectedCaseId();
  if (!caseId) {
    $("auditStatus").textContent = "Select a case before deleting it.";
    return;
  }
  const caseName = selectedCaseTitle() || "this case";
  if (
    !window.confirm(
      `Delete ${caseName}? This removes its notes, uploads, saved runs, and case-specific activity from this account.`,
    )
  ) {
    return;
  }
  const deleteButton = ensureDeleteCaseButton();
  if (deleteButton) {
    deleteButton.disabled = true;
  }
  $("checksPane").textContent = "Deleting case and linked data...";
  setPane("checks");
  try {
    const payload = await postJson("/api/cases", {
      action: "delete",
      case_id: caseId,
    });
    renderCases(payload.cases || []);
    $("caseSelect").value = "";
    state.caseId = "";
    clearCaseDetail();
    $("checksPane").textContent = pretty(payload.summary || payload);
    $("auditStatus").textContent = `Deleted case ${payload.deleted_case.title}.`;
  } catch (error) {
    $("checksPane").textContent = error.message;
    $("auditStatus").textContent = error.message;
  } finally {
    updateCaseActions();
  }
}

async function exportWorkspaceBackup() {
  $("exportWorkspaceButton").disabled = true;
  $("checksPane").textContent = "Building workspace backup...";
  setPane("checks");
  try {
    const payload = await postJson("/api/workspace", { action: "export" });
    renderWorkspaceBackupSummary(payload);
    $("checksPane").textContent = pretty(payload.manifest || payload);
    $("auditStatus").textContent = "Workspace backup generated.";
  } catch (error) {
    $("checksPane").textContent = error.message;
    $("auditStatus").textContent = error.message;
  } finally {
    $("exportWorkspaceButton").disabled = false;
  }
}

async function refreshWorkspaceGovernance() {
  try {
    const payload = await postJson("/api/workspace", { action: "status" });
    renderWorkspaceGovernance(payload);
  } catch (error) {
    $("auditStatus").textContent = error.message;
  }
}

async function pruneWorkspaceRetention() {
  const retentionDays = state.workspacePolicy && state.workspacePolicy.retention_days;
  if (!retentionDays) {
    $("auditStatus").textContent = "This deployment has no retention window configured.";
    return;
  }
  if (!window.confirm(`Prune uploads, saved runs, and audit activity older than ${retentionDays} days?`)) {
    return;
  }
  $("pruneWorkspaceButton").disabled = true;
  $("checksPane").textContent = "Pruning expired workspace data...";
  setPane("checks");
  try {
    const payload = await postJson("/api/workspace", { action: "prune" });
    renderWorkspaceGovernance(payload);
    $("checksPane").textContent = pretty(payload.pruned || payload);
    await loadCases();
    $("auditStatus").textContent = "Expired workspace data pruned.";
  } catch (error) {
    $("checksPane").textContent = error.message;
    $("auditStatus").textContent = error.message;
  } finally {
    $("pruneWorkspaceButton").disabled = false;
  }
}

async function resetWorkspace() {
  if (!window.confirm("Delete all cases, uploads, saved runs, and workspace activity for this account?")) {
    return;
  }
  const confirmText = window.prompt('Type "DELETE WORKSPACE" to continue.');
  if (confirmText !== "DELETE WORKSPACE") {
    $("auditStatus").textContent = "Workspace reset canceled.";
    return;
  }
  $("resetWorkspaceButton").disabled = true;
  $("checksPane").textContent = "Deleting all workspace data...";
  setPane("checks");
  try {
    const payload = await postJson("/api/workspace", {
      action: "reset",
      confirm_text: confirmText,
    });
    renderWorkspaceBackupSummary(null);
    renderWorkspaceGovernance({ policy: payload.policy, summary: { counts: {}, storage: { total_bytes: 0 } } });
    await loadCases();
    $("checksPane").textContent = pretty(payload.summary || payload);
    $("auditStatus").textContent = "Workspace cleared.";
  } catch (error) {
    $("checksPane").textContent = error.message;
    $("auditStatus").textContent = error.message;
  } finally {
    $("resetWorkspaceButton").disabled = false;
  }
}

async function restoreWorkspaceBackup() {
  const file = $("workspaceBackupUpload").files[0];
  if (!file) {
    $("auditStatus").textContent = "Choose a workspace backup .zip first.";
    return;
  }
  if (!window.confirm("Restoring a backup will replace this account's current cases, uploads, and run history. Continue?")) {
    return;
  }
  $("restoreWorkspaceButton").disabled = true;
  $("checksPane").textContent = "Restoring workspace backup...";
  setPane("checks");
  try {
    const backupBase64 = await fileToBase64(file);
    const payload = await postJson("/api/workspace", {
      action: "restore",
      backup_base64: backupBase64,
    });
    renderWorkspaceBackupSummary(null);
    $("workspaceBackupUpload").value = "";
    $("checksPane").textContent = pretty(payload.manifest || payload);
    await loadCases();
    $("auditStatus").textContent = "Workspace restored from backup.";
  } catch (error) {
    $("checksPane").textContent = error.message;
    $("auditStatus").textContent = error.message;
  } finally {
    $("restoreWorkspaceButton").disabled = false;
  }
}

function fileToBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const result = String(reader.result || "");
      resolve(result.includes(",") ? result.split(",", 2)[1] : result);
    };
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(file);
  });
}

async function uploadTemplate() {
  const file = $("templateUpload").files[0];
  if (!file) {
    return;
  }
  setPathDisplay("uploadedTemplatePath", null);
  $("templatePane").textContent = "Uploading template...";
  setPane("template");
  try {
    const contentBase64 = await fileToBase64(file);
    const data = await postJson("/api/upload", {
      filename: file.name,
      content_type: file.type,
      content_base64: contentBase64,
      case_id: selectedCaseId(),
    });
    setSelectedTemplate(
      data.upload.template_ref || "",
      data.upload.original_name || file.name,
      "Template uploaded. You can scan slots or start intelligent drafting now.",
    );
    state.workspacePolicy = data.policy || state.workspacePolicy;
    setPathDisplay("uploadedTemplatePath", data.upload.stored_path, false);
    if (selectedCaseId()) {
      await loadCaseDetail(selectedCaseId());
    }
    await refreshWorkspaceGovernance();
  } catch (error) {
    $("templatePane").textContent = error.message;
  }
}

async function changeWorkspacePassword() {
  if (!state.user) {
    $("auditStatus").textContent = t("password.loginFirst");
    return;
  }
  const currentPassword = $("accountCurrentPassword").value;
  const newPassword = $("accountNewPassword").value;
  const newPasswordConfirm = $("accountNewPasswordConfirm").value;
  if (!currentPassword || !newPassword || !newPasswordConfirm) {
    $("auditStatus").textContent = t("password.fillFields");
    return;
  }
  const button = $("changePasswordButton");
  button.disabled = true;
  try {
    const data = await postJson("/api/account", {
      action: "change_password",
      current_password: currentPassword,
      new_password: newPassword,
      new_password_confirm: newPasswordConfirm,
    });
    state.user = data.user || state.user;
    renderAccountSummary(state.user);
    $("accountCurrentPassword").value = "";
    $("accountNewPassword").value = "";
    $("accountNewPasswordConfirm").value = "";
    $("auditStatus").textContent = data.message || t("password.updated");
  } catch (error) {
    $("auditStatus").textContent = error.message;
  } finally {
    button.disabled = false;
  }
}

function initializeWorkspaceBackupUi() {
  const exportButton = $("exportWorkspaceButton");
  const restoreButton = $("restoreWorkspaceButton");
  if (exportButton) {
    exportButton.textContent = t("workspace.export");
  }
  if (restoreButton) {
    restoreButton.textContent = t("workspace.restore");
  }
  const refreshButton = $("refreshWorkspaceGovernanceButton");
  if (refreshButton) {
    refreshButton.textContent = t("workspace.refresh");
  }
  const pruneButton = $("pruneWorkspaceButton");
  if (pruneButton) {
    pruneButton.textContent = t("workspace.prune");
  }
  const resetButton = $("resetWorkspaceButton");
  if (resetButton) {
    resetButton.textContent = t("workspace.clear");
  }
  const uploadInput = $("workspaceBackupUpload");
  if (uploadInput) {
    const fieldLabel = uploadInput.closest(".field");
    if (fieldLabel) {
      const span = fieldLabel.querySelector("span");
      if (span) {
        span.textContent = t("workspace.backupLabel");
      }
    }
  }
}

document.querySelectorAll(".tab").forEach((button) => {
  button.addEventListener("click", () => setPane(button.dataset.tab));
});

document.querySelectorAll(".accordion-trigger").forEach((button) => {
  button.addEventListener("click", () => {
    const section = button.closest(".accordion-section");
    const nextActive = !section.classList.contains("active");
    document.querySelectorAll(".accordion-section").forEach((item) => {
      item.classList.remove("active");
      item.querySelector(".accordion-trigger").setAttribute("aria-expanded", "false");
    });
    if (nextActive) {
      section.classList.add("active");
      button.setAttribute("aria-expanded", "true");
    }
  });
});

document.addEventListener("pointermove", (event) => {
  document.documentElement.style.setProperty("--mouse-x", `${event.clientX}px`);
  document.documentElement.style.setProperty("--mouse-y", `${event.clientY}px`);
});

$("runButton").addEventListener("click", runAgent);
$("sideCollapseButton").addEventListener("click", () => setSideCollapsed(true));
$("sideExpandButton").addEventListener("click", () => setSideCollapsed(false));
$("sideResizeHandle").addEventListener("pointerdown", beginSideResize);
$("startLoginButton").addEventListener("click", completeIntro);
$("skipIntroButton").addEventListener("click", completeIntro);
$("replayIntroButton").addEventListener("click", (event) => {
  event.preventDefault();
  showIntro();
});
$("localeZhButton").addEventListener("click", () => applyLocale("zh-CN"));
$("localeEnButton").addEventListener("click", () => applyLocale("en"));
$("authModeLogin").addEventListener("click", () => setAuthMode("login"));
$("authModeSignup").addEventListener("click", () => setAuthMode("signup"));
$("loginForm").addEventListener("submit", submitAuthForm);
$("logoutButton").addEventListener("click", logout);
$("createCaseButton").addEventListener("click", createCase);
$("saveCaseButton").addEventListener("click", saveCaseNotes);
$("exportCaseButton").addEventListener("click", exportCasePackage);
ensureDeleteCaseButton().addEventListener("click", deleteCase);
$("exportWorkspaceButton").addEventListener("click", exportWorkspaceBackup);
$("restoreWorkspaceButton").addEventListener("click", restoreWorkspaceBackup);
$("refreshWorkspaceGovernanceButton").addEventListener("click", refreshWorkspaceGovernance);
$("pruneWorkspaceButton").addEventListener("click", pruneWorkspaceRetention);
$("resetWorkspaceButton").addEventListener("click", resetWorkspace);
$("changePasswordButton").addEventListener("click", changeWorkspacePassword);
$("caseSelect").addEventListener("change", () => {
  state.caseId = selectedCaseId();
  updateCaseActions();
  loadCaseDetail(state.caseId);
});
$("templatePath").addEventListener("input", syncTemplateSelectionFromInput);
$("templateUpload").addEventListener("change", uploadTemplate);
$("inspectTemplateButton").addEventListener("click", inspectTemplate);
$("draftTemplateButton").addEventListener("click", draftTemplate);
$("fillTemplateButton").addEventListener("click", fillTemplateFromStructured);

applyLocale(localStorage.getItem(LOCALE_KEY) || DEFAULT_LOCALE);
primeLoginForm();
initializeWorkspaceBackupUi();
updateCaseActions();
applySavedSidePanelState();
updateTemplateAvailability();
clearCaseDetail();
clearDemoCatalog();
renderAccountSummary(null);
renderWorkspaceGovernance(null);
checkSession();
