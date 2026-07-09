import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";
import { fileURLToPath } from "node:url";

class ElementStub {
  constructor(tagName = "div", { hidden = false } = {}) {
    this.tagName = tagName.toUpperCase();
    this.children = [];
    this.textContent = "";
    this._innerHTML = "";
    this.className = "";
    this.hidden = hidden;
    this.classList = { contains: () => false, toggle: () => {} };
  }

  append(...children) {
    this.children.push(...children);
  }

  appendChild(child) {
    this.children.push(child);
    return child;
  }

  removeChild(child) {
    this.children = this.children.filter((item) => item !== child);
  }

  closest() {
    return null;
  }

  get firstChild() {
    return this.children[0] || null;
  }

  set innerHTML(value) {
    this._innerHTML = value;
    if (value === "") this.children = [];
  }

  get innerHTML() {
    return this._innerHTML;
  }
}

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const appPath = path.resolve(scriptDir, "../web-workbench/app.js");
const source = fs.readFileSync(appPath, "utf8");
const bootstrapStart = source.lastIndexOf('document.querySelectorAll(".tab")');
assert.ok(bootstrapStart > 0, "frontend function definitions must load before browser bootstrap");

const elements = new Map();
elements.set("docxPath", new ElementStub("span", { hidden: true }));
elements.set("docxDownloadAction", new ElementStub("div", { hidden: true }));
const getElement = (id) => {
  if (!elements.has(id)) elements.set(id, new ElementStub());
  return elements.get(id);
};
const documentStub = {
  documentElement: { lang: "" },
  getElementById: getElement,
  createElement: (tagName) => new ElementStub(tagName),
  querySelectorAll: () => [],
};
const context = vm.createContext({
  console,
  document: documentStub,
  localStorage: { setItem: () => {}, getItem: () => null },
});
vm.runInContext(source.slice(0, bootstrapStart), context, { filename: appPath });

const indexSource = fs.readFileSync(path.resolve(scriptDir, "../web-workbench/index.html"), "utf8");
const visibleActionIndex = indexSource.indexOf('id="docxDownloadAction"');
assert.ok(visibleActionIndex >= 0, "application markup must include the visible Word action container");
assert.ok(
  visibleActionIndex < indexSource.indexOf('class="app-telemetry"'),
  "visible Word action container must be in the application UI, not hidden telemetry",
);

const payload = {
  status: "success",
  workflow: "W1",
  detected_workflow: "W1",
  workflow_mode: "intake_prep",
  workflow_mode_label: "Initial interview prep",
  workflow_mode_notice: "Using the pre-interview intake guide mode.",
  run_dir: "agent-runs/run-1",
  clean_output: "结构化首访提纲",
  structured_output: { workflow: "W1" },
  docx: {
    status: "PASS",
    path: "agent-runs/run-1/output.docx",
    filename: "output.docx",
    download_url: "/files/agent-runs%2Frun-1%2Foutput.docx",
  },
};

context.__payload = payload;
vm.runInContext('applyLocale("zh-CN"); updateRunResult(__payload);', context);

const modeBox = getElement("workflowModeSummary");
assert.equal(modeBox.children.length, 2, "rendering flow must populate the workflow mode card");
assert.match(modeBox.children[1].textContent, /首访准备/);
assert.doesNotMatch(modeBox.children[1].textContent, /Initial interview prep/);

const telemetryBox = getElement("docxPath");
assert.equal(telemetryBox.hidden, true, "telemetry remains hidden from users and accessibility queries");
const docxBox = getElement("docxDownloadAction");
assert.equal(docxBox.hidden, false, "Word result actions must live in a visible region");
assert.equal(docxBox.children.length, 1, "successful Word output must render one visible download anchor");
const anchor = docxBox.children[0];
assert.equal(anchor.tagName, "A");
assert.equal(anchor.hidden, false);
assert.equal(anchor.href, payload.docx.download_url);
assert.match(anchor.textContent, /下载可编辑 Word 文档/);
assert.match(anchor.textContent, /output\.docx/);

const w2Payload = {
  status: "success",
  workflow: "W2",
  detected_workflow: "W2",
  run_dir: "agent-runs/run-2",
  clean_output: "已生成个案背景整理。",
  structured_output: { workflow: "W2", document_type: "case_summary" },
  docx: {
    status: "PASS",
    path: "agent-runs/run-2/output.docx",
    filename: "output.docx",
    download_url: "/files/agent-runs%2Frun-2%2Foutput.docx",
  },
};

context.__payload = w2Payload;
vm.runInContext('applyLocale("zh-CN"); updateRunResult(__payload);', context);

assert.match(getElement("intentDisplay").textContent, /个案背景|BPS/);
assert.equal(docxBox.hidden, false, "W2 Word output must render in the visible action region");
assert.equal(docxBox.children.length, 1, "W2 successful Word output must render one visible download anchor");
assert.equal(docxBox.children[0].href, w2Payload.docx.download_url);
assert.match(docxBox.children[0].textContent, /Word/);

console.log("web-workbench frontend DOM contract: PASS");
