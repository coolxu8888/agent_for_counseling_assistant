const state = {
  workflow: "W1",
  runDir: null,
  structuredOutput: null,
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

function canFillTemplate() {
  return Boolean(state.runDir && state.structuredOutput);
}

function updateTemplateAvailability() {
  $("fillTemplateButton").disabled = !canFillTemplate();
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
  $("runDir").textContent = data.run_dir || "无";
  $("docxPath").textContent = data.docx && data.docx.path ? data.docx.path : "无";
  updateTemplateAvailability();
}

function showRunError(message) {
  $("checksPane").textContent = message;
  setPane("checks");
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

async function fillTemplate() {
  const templatePath = $("templatePath").value.trim();
  if (!canFillTemplate()) {
    $("templateReport").textContent = "需要先运行并获得结构化 JSON。";
    return;
  }
  if (!templatePath) {
    $("templateReport").textContent = "请输入 Word 模板路径。";
    return;
  }

  $("fillTemplateButton").disabled = true;
  $("templateReport").textContent = "正在填充模板...";

  try {
    const data = await postJson("/api/fill-template", {
      run_dir: state.runDir,
      template_path: templatePath,
    });
    $("filledTemplatePath").textContent = data.output_path || "无";
    $("templateReportPath").textContent = data.report_path || "无";
    $("templateReport").textContent = pretty(data.report);
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
$("fillTemplateButton").addEventListener("click", fillTemplate);
updateTemplateAvailability();
