const state = {
  workflow: "AUTO",
  runDir: null,
  structuredOutput: null,
  templateSlots: [],
  demoCatalog: null,
  user: null,
  authConfig: { signup_enabled: false, invite_required: false },
  authMode: "login",
  caseId: "",
  caseDetail: null,
  selectedTemplateRef: "",
  selectedTemplateLabel: "",
  workspacePolicy: { max_upload_bytes: 10 * 1024 * 1024, retention_days: null, reset_enabled: true },
};

const FALLBACK_DEMO_CATALOG = {
  scenarios: [
    {
      id: "case-family-boundary",
      title: "Recommended demo: W2 case summary",
      workflow: "W2",
      summary: "A de-identified BPS-style case summary request focused on family pressure and uncertainty.",
      input:
        "请整理个案信息。来访者 24 岁，刚入职，最近半年经常因父母催婚和工作绩效焦虑失眠，上周和父亲争执后独自喝了很多酒，但否认自伤想法。已进行过两次校外咨询，目前最困扰的是情绪波动、注意力下降和回避与家人沟通。请区分已知事实、推测和待补充信息。",
      output_style: "supervision_summary",
    },
    {
      id: "intake_sleep-stress",
      title: "W1 Demo: Intake guide",
      workflow: "W1",
      summary: "A de-identified intake request with sleep issues, family stress, and a mild risk prompt.",
      input:
        "请帮我生成初访信息收集表。来访者为大学女生，近两周因保研压力睡眠变差，和室友关系紧张，偶尔说“想消失一下”，但没有计划，也愿意继续上课。咨询师希望准备首访提问提纲，并单独标出需要进一步核实的风险与保护因素。",
      output_style: "professional_concise",
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
  ],
  templates: [],
  privacy_notice: "Use de-identified demo material only. Avoid names, phone numbers, IDs, and real client data in public MVP validation.",
};

const $ = (id) => document.getElementById(id);
const INTRO_KEY = "counselor_agent_intro_seen";
const SIDE_COLLAPSED_KEY = "counselor_agent_side_collapsed";
const SIDE_WIDTH_KEY = "counselor_agent_side_width";
const LOGIN_USERNAME_KEY = "counselor_agent_login_username";

function pretty(value) {
  if (value === null || value === undefined || value === "") {
    return "None";
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

function setPathDisplay(id, path, downloadable = false) {
  const target = $(id);
  if (!target) {
    return;
  }
  clearNode(target);
  if (!path) {
    target.textContent = "None";
    return;
  }
  if (!downloadable) {
    target.textContent = path;
    return;
  }
  const link = document.createElement("a");
  link.className = "download-link";
  link.href = downloadUrl(path);
  link.textContent = path;
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
  $("loginSubmitButton").textContent = signupMode ? "Create workspace" : "Sign in";
  $("authModeLogin").disabled = !signupMode;
  $("authModeSignup").disabled = signupMode;
  $("authModeHint").textContent = signupMode
    ? state.authConfig.invite_required
      ? "Create an isolated counselor workspace with the deployment invite code."
      : "Create an isolated counselor workspace on this deployment."
    : state.authConfig.signup_enabled
      ? "Sign in, or create a separate counselor workspace for pilot use."
      : "Sign in with your assigned workspace credentials.";
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
  return {
    AUTO: "Auto detect",
    W1: "Intake",
    W2: "Case summary",
    W3: "Session note",
    TEMPLATE: "Template draft",
  }[workflow] || workflow;
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

function clearDemoCatalog(message = "Sign in to load one-click demos and built-in templates.") {
  state.demoCatalog = null;
  $("demoCatalogStatus").innerHTML = `<strong>Demo library</strong><span>${message}</span>`;
  addStackPlaceholder("demoStarterList", "De-identified sample workflows will appear here.");
  addStackPlaceholder("demoTemplateList", "Bundled Word templates will appear here.");
}

function applyDemoTemplate(templateRef, title = "template") {
  setSelectedTemplate(
    templateRef,
    title,
    `Built-in template set to ${title}. You can scan slots or start drafting now.`,
  );
  $("auditStatus").textContent = `Loaded built-in template: ${title}.`;
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
  $("markdownPane").textContent = `${scenario.title}

${scenario.summary}

The sample input has been loaded into the composer. Review it and click Run to start a real model call.`;
  setStatus(`Loaded ${workflowLabel(scenario.workflow)} demo`, "idle");
  $("auditStatus").textContent = `Loaded demo scenario: ${scenario.title}.`;
  setPane("markdown");
}

function renderDemoCatalog(payload) {
  state.demoCatalog = payload;
  $("demoCatalogStatus").innerHTML = `<strong>Demo library</strong><span>${payload.privacy_notice || "Use de-identified demo material only."}</span>`;

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
    actions.appendChild(createMiniGhostButton("Load sample", () => applyDemoScenario(scenario.id)));
    card.append(title, summary, actions);
    starterList.appendChild(card);
  });
  if (!starterList.children.length) {
    addStackPlaceholder("demoStarterList", "No demo scenarios are available in this environment.");
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
    actions.appendChild(createMiniGhostButton("Use template", () => applyDemoTemplate(template.template_ref, template.title)));
    card.append(title, summary, actions);
    templateList.appendChild(card);
  });
  if (!templateList.children.length) {
    addStackPlaceholder("demoTemplateList", "No bundled Word templates were found.");
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

function renderWorkspaceGovernance(data) {
  const box = $("workspaceGovernanceSummary");
  if (!box) {
    return;
  }
  const policy = (data && data.policy) || state.workspacePolicy || {};
  if (data && data.policy) {
    state.workspacePolicy = data.policy;
  }
  const summary = (data && data.summary) || null;
  box.innerHTML = "";
  const title = document.createElement("strong");
  title.textContent = "Data controls";
  const body = document.createElement("span");
  if (!summary) {
    body.textContent = "Review storage, upload limits, and retention before using hosted pilot data.";
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

function updateRunResult(data) {
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
  setPathDisplay("docxPath", data.docx && data.docx.path ? data.docx.path : null, true);
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
  $("loginMessage").textContent = signupMode ? "Creating workspace..." : "Signing in...";
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
    localStorage.setItem(LOGIN_USERNAME_KEY, data.user.username);
    hideLogin();
    await Promise.all([loadCases(), loadDemoCatalog(), refreshWorkspaceGovernance()]);
    $("auditStatus").textContent = `Signed in as ${data.user.username}`;
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
  $("caseSelect").innerHTML = '<option value="">No case selected</option>';
  clearCaseDetail();
  clearDemoCatalog();
  renderWorkspaceGovernance(null);
  showLogin("Signed out.");
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
    if (data.authenticated) {
      state.user = data.user;
      hideLogin();
      await Promise.all([loadCases(), loadDemoCatalog(), refreshWorkspaceGovernance()]);
      $("auditStatus").textContent = `Signed in as ${data.user.username}`;
    } else {
      clearDemoCatalog();
      renderWorkspaceGovernance(null);
      showLogin();
    }
  } catch (error) {
    clearDemoCatalog();
    renderWorkspaceGovernance(null);
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

function initializeWorkspaceBackupUi() {
  const exportButton = $("exportWorkspaceButton");
  const restoreButton = $("restoreWorkspaceButton");
  if (exportButton) {
    exportButton.textContent = "Backup workspace";
  }
  if (restoreButton) {
    restoreButton.textContent = "Restore backup";
  }
  const refreshButton = $("refreshWorkspaceGovernanceButton");
  if (refreshButton) {
    refreshButton.textContent = "Refresh data status";
  }
  const pruneButton = $("pruneWorkspaceButton");
  if (pruneButton) {
    pruneButton.textContent = "Prune expired data";
  }
  const resetButton = $("resetWorkspaceButton");
  if (resetButton) {
    resetButton.textContent = "Clear workspace";
  }
  const uploadInput = $("workspaceBackupUpload");
  if (uploadInput) {
    const fieldLabel = uploadInput.closest(".field");
    if (fieldLabel) {
      const span = fieldLabel.querySelector("span");
      if (span) {
        span.textContent = "Workspace backup (.zip)";
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

primeLoginForm();
initializeWorkspaceBackupUi();
updateCaseActions();
applySavedSidePanelState();
updateTemplateAvailability();
clearCaseDetail();
clearDemoCatalog();
renderWorkspaceGovernance(null);
checkSession();
