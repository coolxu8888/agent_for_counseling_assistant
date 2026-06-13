const state = {
  workflow: "W1",
  runDir: null,
  structuredOutput: null,
  templateSlots: [],
};

const $ = (id) => document.getElementById(id);

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
    throw new Error(data.message || "请求失败。");
  }
  return data;
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
  setPathDisplay("runDir", data.run_dir, false);
  setPathDisplay("docxPath", data.docx && data.docx.path ? data.docx.path : null, true);
  updateTemplateAvailability();
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
  $("templateReport").textContent = formatReportSummary(data.report);
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
    $("templateReport").textContent = "请输入 Word 模板路径。";
    return;
  }
  if (!rawInput) {
    $("templateReport").textContent = "请输入咨询师材料。智能填充需要 raw data。";
    return;
  }

  $("draftTemplateButton").disabled = true;
  $("fillTemplateButton").disabled = true;
  $("templateReport").textContent = "正在理解模板并整理填充内容...";

  try {
    const data = await postJson("/api/draft-template", {
      ...templatePayloadBase(),
      raw_input: rawInput,
      style: $("styleSelect").value,
      custom_style: $("customStyle").value.trim(),
      existing_content_policy: $("existingPolicy").value,
      run_dir: state.runDir,
    });
    updateTemplateResult(data);
  } catch (error) {
    $("templateReport").textContent = error.message;
  } finally {
    $("draftTemplateButton").disabled = false;
    updateTemplateAvailability();
  }
}

async function inspectTemplate() {
  const templatePath = $("templatePath").value.trim();
  if (!templatePath) {
    $("templateSummary").innerHTML = "<strong>模板识别</strong><span>请输入 Word 模板路径。</span>";
    return;
  }

  $("inspectTemplateButton").disabled = true;
  $("templateSummary").innerHTML = "<strong>模板识别</strong><span>正在扫描模板栏目...</span>";

  try {
    const data = await postJson("/api/inspect-template", templatePayloadBase());
    state.templateSlots = data.slots || [];
    $("templateSummary").innerHTML = "";
    const title = document.createElement("strong");
    title.textContent = "模板识别";
    const body = document.createElement("span");
    body.textContent = formatTemplateSummary(data);
    $("templateSummary").append(title, body);
  } catch (error) {
    state.templateSlots = [];
    $("templateSummary").innerHTML = "";
    const title = document.createElement("strong");
    title.textContent = "模板识别失败";
    const body = document.createElement("span");
    body.textContent = error.message;
    $("templateSummary").append(title, body);
  } finally {
    $("inspectTemplateButton").disabled = false;
  }
}

async function fillTemplateFromStructured() {
  const templatePath = $("templatePath").value.trim();
  if (!canFillFromStructured()) {
    $("templateReport").textContent = "需要先运行并获得结构化 JSON，或者使用上方智能模板填充。";
    return;
  }
  if (!templatePath) {
    $("templateReport").textContent = "请输入 Word 模板路径。";
    return;
  }

  $("fillTemplateButton").disabled = true;
  $("templateReport").textContent = "正在用结构化 JSON 填充模板...";

  try {
    const data = await postJson("/api/fill-template", {
      run_dir: state.runDir,
      ...templatePayloadBase(),
    });
    updateTemplateResult(data);
  } catch (error) {
    $("templateReport").textContent = error.message;
  } finally {
    updateTemplateAvailability();
  }
}

document.querySelectorAll(".workflow").forEach((button) => {
  button.addEventListener("click", () => {
    state.workflow = button.dataset.workflow;
    document.querySelectorAll(".workflow").forEach((item) => item.classList.toggle("active", item === button));
  });
});

document.querySelectorAll(".tab").forEach((button) => {
  button.addEventListener("click", () => setPane(button.dataset.tab));
});

$("runButton").addEventListener("click", runAgent);
$("inspectTemplateButton").addEventListener("click", inspectTemplate);
$("draftTemplateButton").addEventListener("click", draftTemplate);
$("fillTemplateButton").addEventListener("click", fillTemplateFromStructured);
updateTemplateAvailability();
