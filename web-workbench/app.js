const state = {
  workflow: "AUTO",
  runDir: null,
  structuredOutput: null,
  templateSlots: [],
  user: null,
  caseId: "",
};

const $ = (id) => document.getElementById(id);
const INTRO_KEY = "counselor_agent_intro_seen";

function pretty(value) {
  if (value === null || value === undefined || value === "") {
    return "无";
  }
  if (typeof value === "string") {
    return value;
  }
  return JSON.stringify(value, null, 2);
}

function downloadUrl(path) {
  return `/files/${encodeURIComponent(path)}`;
}

function setPathDisplay(id, path, downloadable = false) {
  const target = $(id);
  target.textContent = "";
  if (!path) {
    target.textContent = "无";
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

function setPane(tabName) {
  document.querySelectorAll(".tab").forEach((tab) => {
    const active = tab.dataset.tab === tabName;
    tab.classList.toggle("active", active);
    tab.setAttribute("aria-selected", String(active));
  });

  document.querySelectorAll(".pane").forEach((pane) => pane.classList.remove("active"));
  const paneId = tabName === "markdown" ? "markdownPane" : tabName === "json" ? "jsonPane" : "checksPane";
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
  } catch (error) {
    data = { message: "响应不是有效 JSON。" };
  }

  if (!response.ok) {
    if (response.status === 401) {
      showLogin();
    }
    throw new Error(data.message || "请求失败。");
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
    throw new Error(data.message || "请求失败。");
  }
  return data;
}

function showLogin(message = "") {
  $("loginOverlay").classList.remove("hidden");
  $("loginMessage").textContent = message;
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

function selectedCaseId() {
  return $("caseSelect").value || "";
}

function canFillFromStructured() {
  return Boolean(state.runDir && state.structuredOutput);
}

function updateTemplateAvailability() {
  $("fillTemplateButton").disabled = !canFillFromStructured();
}

function formatTemplateSummary(data) {
  const summary = data.summary || {};
  const slots = data.slots || [];
  const typeText = Object.entries(summary.slot_types || {})
    .map(([type, count]) => `${type}: ${count}`)
    .join("；") || "无";
  const preview = slots
    .slice(0, 30)
    .map((slot, index) => {
      const current = slot.current_text && slot.current_text !== slot.label ? `｜当前：${slot.current_text}` : "";
      return `${index + 1}. ${slot.label || "未命名栏目"}（${slot.slot_type}）${current}`;
    })
    .join("\n");
  const more = slots.length > 30 ? `\n... 还有 ${slots.length - 30} 个栏目未显示` : "";
  return [
    `识别栏目：${summary.total_slots || 0} 个`,
    `可填空位：${summary.fillable_slots || 0} 个`,
    `已有内容：${summary.prefilled_slots || 0} 个`,
    `栏目类型：${typeText}`,
    "",
    preview || "没有识别到可填栏目。模板可能不是普通表格/冒号占位格式，或内容在文本框、图片、复杂控件中。",
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
    `状态：${report.status || "未知"}`,
    `已填字段：${filled.length}`,
    `模型草稿写入：${drafted.length}`,
    `保留原内容：${kept.length}`,
    `跳过字段：${skipped.length}`,
    `未填字段：${unfilled.length}`,
    `警告/问题：${issues.length}`,
  ];
  const important = [...unfilled, ...skipped, ...issues].slice(0, 12);
  if (important.length) {
    lines.push("", "需要查看的项目：");
    important.forEach((item, index) => {
      const label = item.template_label || item.location || item.slot_id || "未命名";
      const reason = item.reason || item.message || "未说明";
      lines.push(`${index + 1}. ${label}：${reason}`);
    });
  }
  lines.push("", "完整报告：", pretty(report));
  return lines.join("\n");
}

function updateRunResult(data) {
  state.runDir = data.run_dir || null;
  state.structuredOutput = data.structured_output || null;

  $("markdownPane").textContent = data.clean_output || data.raw_output || "无模型输出。";
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

function workflowLabel(workflow) {
  return {
    AUTO: "自动判断",
    W1: "初访信息",
    W2: "个案整理",
    W3: "咨询记录",
  }[workflow] || workflow;
}

function showRunError(message) {
  $("checksPane").textContent = message;
  setPane("checks");
}

function updateTemplateResult(data) {
  if (data.run_dir) {
    state.runDir = data.run_dir;
    $("runDir").textContent = data.run_dir;
  }
  setPathDisplay("filledTemplatePath", data.output_path, true);
  setPathDisplay("templateDraftPath", data.draft_path, true);
  setPathDisplay("templateReportPath", data.report_path, true);
  $("templatePane").textContent = formatReportSummary(data.report);
  setPane("template");
  updateTemplateAvailability();
}

function templatePayloadBase() {
  return {
    template_path: $("templatePath").value.trim(),
  };
}

async function runAgent() {
  const input = $("inputText").value.trim();
  if (!input) {
    setStatus("缺少输入", "error");
    showRunError("请输入咨询师材料后再运行。");
    return;
  }

  setStatus("运行中", "running");
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
    setStatus(data.status === "success" ? "成功" : data.status || "完成", data.status === "error" ? "error" : "success");
  } catch (error) {
    state.runDir = null;
    state.structuredOutput = null;
    updateTemplateAvailability();
    setStatus("失败", "error");
    showRunError(error.message);
  } finally {
    $("runButton").disabled = false;
  }
}

async function draftTemplate() {
  const templatePath = $("templatePath").value.trim();
  const rawInput = $("inputText").value.trim();
  if (!templatePath) {
    $("templatePane").textContent = "请输入 Word 模板路径。";
    setPane("template");
    return;
  }
  if (!rawInput) {
    $("templatePane").textContent = "请输入咨询师材料。智能填充需要 raw data。";
    setPane("template");
    return;
  }

  $("draftTemplateButton").disabled = true;
  $("fillTemplateButton").disabled = true;
  $("templatePane").textContent = "正在理解模板并整理填充内容...";
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
    $("templateSummary").innerHTML = "<strong>模板识别</strong><span>请输入 Word 模板路径。</span>";
    $("templatePane").textContent = "请输入 Word 模板路径。";
    setPane("template");
    return;
  }

  $("inspectTemplateButton").disabled = true;
  $("templateSummary").innerHTML = "<strong>模板识别</strong><span>正在扫描模板栏目...</span>";
  $("templatePane").textContent = "正在扫描模板栏目...";
  setPane("template");

  try {
    const data = await postJson("/api/inspect-template", templatePayloadBase());
    state.templateSlots = data.slots || [];
    $("templateSummary").innerHTML = "";
    const title = document.createElement("strong");
    title.textContent = "模板识别";
    const body = document.createElement("span");
    body.textContent = formatTemplateSummary(data);
    $("templateSummary").append(title, body);
    $("templatePane").textContent = formatTemplateSummary(data);
  } catch (error) {
    state.templateSlots = [];
    $("templateSummary").innerHTML = "";
    const title = document.createElement("strong");
    title.textContent = "模板识别失败";
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
    $("templatePane").textContent = "需要先运行并获得结构化 JSON，或者使用上方智能模板填充。";
    setPane("template");
    return;
  }
  if (!templatePath) {
    $("templatePane").textContent = "请输入 Word 模板路径。";
    setPane("template");
    return;
  }

  $("fillTemplateButton").disabled = true;
  $("templatePane").textContent = "正在用结构化 JSON 填充模板...";
  setPane("template");

  try {
    const data = await postJson("/api/fill-template", {
      run_dir: state.runDir,
      ...templatePayloadBase(),
    });
    updateTemplateResult(data);
  } catch (error) {
    $("templatePane").textContent = error.message;
    setPane("template");
  } finally {
    updateTemplateAvailability();
  }
}

async function login(event) {
  event.preventDefault();
  $("loginMessage").textContent = "登录中...";
  try {
    const data = await postJson("/api/login", {
      username: $("loginUsername").value.trim(),
      password: $("loginPassword").value,
    });
    state.user = data.user;
    hideLogin();
    await loadCases();
    $("auditStatus").textContent = `已登录：${data.user.username}`;
  } catch (error) {
    $("loginMessage").textContent = error.message;
  }
}

async function logout() {
  await postJson("/api/logout", {});
  state.user = null;
  state.caseId = "";
  $("caseSelect").innerHTML = '<option value="">未选择个案</option>';
  showLogin("已退出登录。");
}

async function checkSession() {
  try {
    if (shouldShowIntro()) {
      showIntro();
      return;
    }
    const data = await getJson("/api/session");
    if (data.authenticated) {
      state.user = data.user;
      hideLogin();
      await loadCases();
      $("auditStatus").textContent = `已登录：${data.user.username}`;
    } else {
      showLogin();
    }
  } catch (error) {
    showLogin(error.message);
  }
}

function renderCases(cases) {
  const select = $("caseSelect");
  const current = select.value;
  select.innerHTML = '<option value="">未选择个案</option>';
  cases.forEach((caseItem) => {
    const option = document.createElement("option");
    option.value = String(caseItem.id);
    option.textContent = caseItem.client_code
      ? `${caseItem.title}（${caseItem.client_code}）`
      : caseItem.title;
    select.appendChild(option);
  });
  if ([...select.options].some((option) => option.value === current)) {
    select.value = current;
  }
  state.caseId = select.value;
}

async function loadCases() {
  const data = await postJson("/api/cases", {});
  renderCases(data.cases || []);
}

async function createCase() {
  const title = $("caseTitleInput").value.trim();
  if (!title) {
    $("auditStatus").textContent = "请先输入个案标题。";
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
  $("caseTitleInput").value = "";
  $("clientCodeInput").value = "";
  $("auditStatus").textContent = "个案已创建。";
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
  $("templatePane").textContent = "正在上传模板...";
  setPane("template");
  try {
    const contentBase64 = await fileToBase64(file);
    const data = await postJson("/api/upload", {
      filename: file.name,
      content_type: file.type,
      content_base64: contentBase64,
      case_id: selectedCaseId(),
    });
    $("templatePath").value = data.upload.stored_path;
    setPathDisplay("uploadedTemplatePath", data.upload.stored_path, false);
    $("templatePane").textContent = "模板已上传，可以扫描栏目或智能填充。";
  } catch (error) {
    $("templatePane").textContent = error.message;
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
$("startLoginButton").addEventListener("click", completeIntro);
$("skipIntroButton").addEventListener("click", completeIntro);
$("replayIntroButton").addEventListener("click", (event) => {
  event.preventDefault();
  showIntro();
});
$("loginForm").addEventListener("submit", login);
$("logoutButton").addEventListener("click", logout);
$("createCaseButton").addEventListener("click", createCase);
$("caseSelect").addEventListener("change", () => {
  state.caseId = selectedCaseId();
});
$("templateUpload").addEventListener("change", uploadTemplate);
$("inspectTemplateButton").addEventListener("click", inspectTemplate);
$("draftTemplateButton").addEventListener("click", draftTemplate);
$("fillTemplateButton").addEventListener("click", fillTemplateFromStructured);
updateTemplateAvailability();
checkSession();
