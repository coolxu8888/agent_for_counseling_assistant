# Local Web Workbench Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local browser workbench for running W1/W2/W3, inspecting Markdown/JSON/check results, rendering fixed DOCX output, and filling counselor-provided DOCX templates.

**Architecture:** Add a small Python standard-library HTTP server that wraps the existing agent, DOCX renderer, and template filler functions. Serve a static HTML/CSS/JS interface with the approved layout: left workflow navigation, center result panes, bottom input/run controls, and right template fill panel. Keep all generated files under `agent-runs/` and guard file downloads so the workbench cannot browse arbitrary local files.

**Tech Stack:** Python standard library `http.server`, existing Python scripts, static HTML/CSS/JavaScript, `unittest`.

---

## File Structure

- Create `scripts/web_workbench.py`
  - Owns local HTTP routing, JSON request/response helpers, path safety, and calls to `run_agent_once()`, `render_docx()`, and `fill_docx_template()`.
  - Uses no external web framework in v0.1.
- Create `scripts/run-web-workbench.ps1`
  - PowerShell wrapper that starts the local workbench server.
- Create `web-workbench/index.html`
  - Static workbench shell with four regions: left workflow navigation, center result observer, bottom input controls, right template panel.
- Create `web-workbench/styles.css`
  - Workbench layout and visual styling.
- Create `web-workbench/app.js`
  - Browser state, API calls, tab switching, result rendering, run status, and template fill actions.
- Create `scripts/test_web_workbench.py`
  - Unit tests for request handling, mocked agent runs, template fill endpoint, and file-serving path guard.
- Modify `README.md`
  - Add local workbench startup and usage notes.

---

### Task 1: Add The Local Web Server Skeleton

**Files:**
- Create: `scripts/web_workbench.py`
- Test: `scripts/test_web_workbench.py`

- [ ] **Step 1: Write failing tests for JSON helpers and static index serving**

Create `scripts/test_web_workbench.py`:

```python
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import web_workbench


class WebWorkbenchTest(unittest.TestCase):
    def test_json_response_encodes_utf8_payload(self):
        status, headers, body = web_workbench.json_response({"message": "咨询师助理"})

        self.assertEqual(status, 200)
        self.assertEqual(headers["Content-Type"], "application/json; charset=utf-8")
        self.assertEqual(json.loads(body.decode("utf-8")), {"message": "咨询师助理"})

    def test_error_response_uses_error_shape(self):
        status, headers, body = web_workbench.error_response(400, "Missing input")

        self.assertEqual(status, 400)
        self.assertEqual(headers["Content-Type"], "application/json; charset=utf-8")
        self.assertEqual(json.loads(body.decode("utf-8")), {"status": "error", "message": "Missing input"})

    def test_static_file_path_resolves_inside_web_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            web_root = Path(tmp) / "web-workbench"
            web_root.mkdir()
            index_path = web_root / "index.html"
            index_path.write_text("<h1>ok</h1>", encoding="utf-8")

            resolved = web_workbench.resolve_static_path("/", web_root)

        self.assertEqual(resolved.name, "index.html")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
python -m unittest scripts.test_web_workbench
```

Expected: FAIL because `scripts/web_workbench.py` does not exist or functions are missing.

- [ ] **Step 3: Implement minimal server helpers**

Create `scripts/web_workbench.py`:

```python
import argparse
import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse


ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = ROOT / "web-workbench"
RUN_ROOT = ROOT / "agent-runs"


def json_response(payload, status=200):
    body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    return status, {"Content-Type": "application/json; charset=utf-8"}, body


def error_response(status, message, issues=None):
    payload = {"status": "error", "message": message}
    if issues:
        payload["issues"] = issues
    return json_response(payload, status=status)


def resolve_static_path(request_path, web_root=WEB_ROOT):
    parsed_path = unquote(urlparse(request_path).path)
    if parsed_path == "/":
        parsed_path = "/index.html"
    candidate = (Path(web_root) / parsed_path.lstrip("/")).resolve()
    root = Path(web_root).resolve()
    if root != candidate and root not in candidate.parents:
        raise ValueError("Static path is outside web root.")
    if not candidate.is_file():
        raise FileNotFoundError(str(candidate))
    return candidate


def read_json_body(handler):
    content_length = int(handler.headers.get("Content-Length", "0") or "0")
    if content_length <= 0:
        return {}
    raw = handler.rfile.read(content_length)
    return json.loads(raw.decode("utf-8"))


def send_response_tuple(handler, response):
    status, headers, body = response
    handler.send_response(status)
    for key, value in headers.items():
        handler.send_header(key, value)
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


class WorkbenchHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            path = resolve_static_path(self.path)
            body = path.read_bytes()
            content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
            send_response_tuple(self, (200, {"Content-Type": content_type}, body))
        except FileNotFoundError:
            send_response_tuple(self, error_response(404, "File not found."))
        except Exception as exc:
            send_response_tuple(self, error_response(400, str(exc)))

    def do_POST(self):
        send_response_tuple(self, error_response(404, "Endpoint not found."))


def create_server(host="127.0.0.1", port=8765):
    return ThreadingHTTPServer((host, port), WorkbenchHandler)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Start the local counselor-agent web workbench.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    server = create_server(args.host, args.port)
    print(f"Workbench running at http://{args.host}:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run tests**

Run:

```powershell
python -m unittest scripts.test_web_workbench
```

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```powershell
git add scripts/web_workbench.py scripts/test_web_workbench.py
git commit -m "Add local workbench server skeleton"
```

---

### Task 2: Add Agent Run API

**Files:**
- Modify: `scripts/web_workbench.py`
- Modify: `scripts/test_web_workbench.py`

- [ ] **Step 1: Write failing tests for `/api/run` behavior**

Append tests to `scripts/test_web_workbench.py`:

```python
    def test_handle_run_rejects_empty_input(self):
        response = web_workbench.handle_api_run({"workflow": "W1", "input": "   "})

        status, _headers, body = response
        self.assertEqual(status, 400)
        self.assertIn("Input is required", json.loads(body.decode("utf-8"))["message"])

    def test_handle_run_returns_saved_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "agent-runs" / "run-1"
            run_dir.mkdir(parents=True)
            (run_dir / "clean_output.md").write_text("clean answer", encoding="utf-8")
            (run_dir / "structured_output.json").write_text('{"workflow": "W1"}', encoding="utf-8")
            (run_dir / "structured_check.json").write_text('{"status": "PASS"}', encoding="utf-8")
            (run_dir / "safety_check.json").write_text('{"status": "PASS", "rubric_status": "PASS"}', encoding="utf-8")
            (run_dir / "metadata.json").write_text('{"status": "success"}', encoding="utf-8")

            fake_result = web_workbench.AgentRunResult("W1", "success", run_dir)
            with patch.object(web_workbench, "run_agent_once", return_value=fake_result):
                status, _headers, body = web_workbench.handle_api_run(
                    {"workflow": "W1", "input": "材料", "structured": True, "render_docx": False}
                )

        payload = json.loads(body.decode("utf-8"))
        self.assertEqual(status, 200)
        self.assertEqual(payload["status"], "success")
        self.assertEqual(payload["workflow"], "W1")
        self.assertEqual(payload["clean_output"], "clean answer")
        self.assertEqual(payload["structured_output"], {"workflow": "W1"})
        self.assertEqual(payload["structured_check"], {"status": "PASS"})
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
python -m unittest scripts.test_web_workbench
```

Expected: FAIL because `handle_api_run` and `AgentRunResult` import do not exist.

- [ ] **Step 3: Implement run endpoint helpers**

Modify imports in `scripts/web_workbench.py`:

```python
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from run_agent import AgentRunResult, run_agent_once
```

Add helpers:

```python
def read_text_if_exists(path):
    path = Path(path)
    return path.read_text(encoding="utf-8") if path.exists() else ""


def read_json_if_exists(path):
    path = Path(path)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def path_for_ui(path):
    return str(Path(path).resolve())


def load_run_payload(result):
    run_dir = Path(result.run_dir)
    structured_output = read_json_if_exists(run_dir / "structured_output.json")
    structured_check = read_json_if_exists(run_dir / "structured_check.json")
    safety_check = read_json_if_exists(run_dir / "safety_check.json")
    metadata = read_json_if_exists(run_dir / "metadata.json")
    docx_check = read_json_if_exists(run_dir / "docx_check.json")
    docx_path = run_dir / "output.docx"
    return {
        "status": result.status,
        "workflow": result.workflow_id,
        "run_dir": path_for_ui(run_dir),
        "clean_output": read_text_if_exists(run_dir / "clean_output.md"),
        "raw_output": read_text_if_exists(run_dir / "raw_output.txt"),
        "structured_output": structured_output,
        "structured_check": structured_check,
        "safety_check": safety_check,
        "metadata": metadata,
        "docx": {
            "status": docx_check["status"] if isinstance(docx_check, dict) and "status" in docx_check else "skipped",
            "path": path_for_ui(docx_path) if docx_path.exists() else None,
            "check": docx_check,
        },
        "issues": [],
    }


def handle_api_run(payload):
    workflow = str(payload.get("workflow", "W1")).strip() or "W1"
    user_input = str(payload.get("input", "")).strip()
    if not user_input:
        return error_response(400, "Input is required.")
    structured = bool(payload.get("structured", True))
    render_docx = bool(payload.get("render_docx", False))
    dry_run = bool(payload.get("dry_run", False))
    try:
        result = run_agent_once(
            workflow,
            inline_input=user_input,
            dry_run=dry_run,
            structured=structured or render_docx,
            docx=render_docx,
        )
        return json_response(load_run_payload(result))
    except Exception as exc:
        return error_response(500, str(exc))
```

Update `WorkbenchHandler.do_POST`:

```python
    def do_POST(self):
        try:
            payload = read_json_body(self)
            if self.path == "/api/run":
                send_response_tuple(self, handle_api_run(payload))
                return
            send_response_tuple(self, error_response(404, "Endpoint not found."))
        except json.JSONDecodeError:
            send_response_tuple(self, error_response(400, "Invalid JSON request."))
        except Exception as exc:
            send_response_tuple(self, error_response(500, str(exc)))
```

- [ ] **Step 4: Run tests**

Run:

```powershell
python -m unittest scripts.test_web_workbench
```

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```powershell
git add scripts/web_workbench.py scripts/test_web_workbench.py
git commit -m "Expose agent run API for workbench"
```

---

### Task 3: Add Fixed DOCX And Template Fill APIs

**Files:**
- Modify: `scripts/web_workbench.py`
- Modify: `scripts/test_web_workbench.py`

- [ ] **Step 1: Write failing tests for DOCX endpoints**

Append tests:

```python
    def test_handle_render_docx_requires_structured_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run"
            run_dir.mkdir()
            status, _headers, body = web_workbench.handle_render_docx({"run_dir": str(run_dir)})

        self.assertEqual(status, 400)
        self.assertIn("structured_output.json", json.loads(body.decode("utf-8"))["message"])

    def test_handle_fill_template_uses_current_structured_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run"
            run_dir.mkdir()
            structured = run_dir / "structured_output.json"
            structured.write_text('{"workflow": "W1"}', encoding="utf-8")
            template = Path(tmp) / "template.docx"
            template.write_bytes(b"fake docx")

            def fake_fill(template_path, structured_path, output_path, report_path, mapping_path=None):
                Path(output_path).write_bytes(b"filled")
                report = {"status": "PASS", "filled_fields": [{"template_label": "A"}], "unfilled_fields": [], "issues": []}
                Path(report_path).write_text(json.dumps(report), encoding="utf-8")
                return report

            with patch.object(web_workbench, "fill_docx_template", side_effect=fake_fill):
                status, _headers, body = web_workbench.handle_fill_template(
                    {"run_dir": str(run_dir), "template_path": str(template)}
                )

        payload = json.loads(body.decode("utf-8"))
        self.assertEqual(status, 200)
        self.assertEqual(payload["status"], "success")
        self.assertTrue(payload["output_path"].endswith("filled_template.docx"))
        self.assertEqual(payload["report"]["status"], "PASS")
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
python -m unittest scripts.test_web_workbench
```

Expected: FAIL because DOCX handlers are missing.

- [ ] **Step 3: Implement DOCX handlers**

Add imports:

```python
from fill_docx_template import fill_docx_template
from render_docx import render_docx
```

Add helper:

```python
def require_run_file(run_dir_value, filename):
    run_dir = Path(str(run_dir_value)).resolve()
    target = run_dir / filename
    if not target.exists():
        raise FileNotFoundError(f"{filename} not found in run directory.")
    return run_dir, target
```

Add endpoint handlers:

```python
def handle_render_docx(payload):
    try:
        run_dir, structured_path = require_run_file(payload.get("run_dir", ""), "structured_output.json")
        data = json.loads(structured_path.read_text(encoding="utf-8"))
        output_path = run_dir / "output.docx"
        check = render_docx(data, output_path)
        check_path = run_dir / "docx_check.json"
        check_path.write_text(json.dumps(check, ensure_ascii=False, indent=2), encoding="utf-8")
        return json_response(
            {
                "status": "success" if check.get("status") != "FAIL" else "error",
                "output_path": path_for_ui(output_path) if output_path.exists() else None,
                "check_path": path_for_ui(check_path),
                "check": check,
            },
            status=200 if check.get("status") != "FAIL" else 500,
        )
    except FileNotFoundError as exc:
        return error_response(400, str(exc))
    except Exception as exc:
        return error_response(500, str(exc))


def handle_fill_template(payload):
    try:
        run_dir, structured_path = require_run_file(payload.get("run_dir", ""), "structured_output.json")
        template_path = Path(str(payload.get("template_path", ""))).expanduser().resolve()
        if not template_path.exists():
            return error_response(400, "Template file not found.")
        output_path = run_dir / "filled_template.docx"
        report_path = run_dir / "template_fill_report.json"
        report = fill_docx_template(template_path, structured_path, output_path, report_path)
        status_code = 200 if report.get("status") != "FAIL" else 500
        return json_response(
            {
                "status": "success" if report.get("status") != "FAIL" else "error",
                "output_path": path_for_ui(output_path) if output_path.exists() else None,
                "report_path": path_for_ui(report_path),
                "report": report,
            },
            status=status_code,
        )
    except FileNotFoundError as exc:
        return error_response(400, str(exc))
    except Exception as exc:
        return error_response(500, str(exc))
```

Route in `do_POST`:

```python
            if self.path == "/api/render-docx":
                send_response_tuple(self, handle_render_docx(payload))
                return
            if self.path == "/api/fill-template":
                send_response_tuple(self, handle_fill_template(payload))
                return
```

- [ ] **Step 4: Run tests**

Run:

```powershell
python -m unittest scripts.test_web_workbench
```

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```powershell
git add scripts/web_workbench.py scripts/test_web_workbench.py
git commit -m "Add workbench DOCX APIs"
```

---

### Task 4: Add Safe File Download Endpoint

**Files:**
- Modify: `scripts/web_workbench.py`
- Modify: `scripts/test_web_workbench.py`

- [ ] **Step 1: Write failing tests for path guard**

Append tests:

```python
    def test_resolve_download_path_allows_agent_runs_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_root = root / "agent-runs"
            run_root.mkdir()
            output = run_root / "file.docx"
            output.write_bytes(b"docx")

            resolved = web_workbench.resolve_download_path(str(output), allowed_roots=[run_root])

        self.assertEqual(resolved.name, "file.docx")

    def test_resolve_download_path_rejects_outside_agent_runs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_root = root / "agent-runs"
            run_root.mkdir()
            outside = root / "secret.txt"
            outside.write_text("secret", encoding="utf-8")

            with self.assertRaises(ValueError):
                web_workbench.resolve_download_path(str(outside), allowed_roots=[run_root])
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
python -m unittest scripts.test_web_workbench
```

Expected: FAIL because `resolve_download_path` does not exist.

- [ ] **Step 3: Implement file path guard and route**

Add:

```python
def is_relative_to(path, root):
    path = Path(path).resolve()
    root = Path(root).resolve()
    return path == root or root in path.parents


def resolve_download_path(path_value, allowed_roots=None):
    allowed_roots = allowed_roots or [RUN_ROOT]
    candidate = Path(str(path_value)).resolve()
    if not candidate.is_file():
        raise FileNotFoundError(str(candidate))
    if not any(is_relative_to(candidate, root) for root in allowed_roots):
        raise ValueError("Download path is outside approved output directories.")
    return candidate


def handle_file_download(request_path):
    parsed = urlparse(request_path)
    if not parsed.path.startswith("/files/"):
        return error_response(404, "File endpoint not found.")
    encoded_path = parsed.path[len("/files/") :]
    target = resolve_download_path(unquote(encoded_path))
    body = target.read_bytes()
    return (
        200,
        {
            "Content-Type": mimetypes.guess_type(target.name)[0] or "application/octet-stream",
            "Content-Disposition": f'attachment; filename="{target.name}"',
        },
        body,
    )
```

Update `do_GET` before static serving:

```python
            if self.path.startswith("/files/"):
                send_response_tuple(self, handle_file_download(self.path))
                return
```

- [ ] **Step 4: Run tests**

Run:

```powershell
python -m unittest scripts.test_web_workbench
```

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```powershell
git add scripts/web_workbench.py scripts/test_web_workbench.py
git commit -m "Guard workbench file downloads"
```

---

### Task 5: Add Static Workbench UI

**Files:**
- Create: `web-workbench/index.html`
- Create: `web-workbench/styles.css`
- Create: `web-workbench/app.js`

- [ ] **Step 1: Create HTML shell**

Create `web-workbench/index.html`:

```html
<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>咨询师助理工作台</title>
    <link rel="stylesheet" href="/styles.css" />
  </head>
  <body>
    <main class="workbench">
      <aside class="workflow-rail" aria-label="工作流">
        <header class="brand">
          <h1>咨询师助理</h1>
          <span id="runStatus" class="status idle">未运行</span>
        </header>
        <button class="workflow active" data-workflow="W1">
          <strong>W1 初访信息收集</strong>
          <span>初访前提问表；明确要求时整理初始访谈材料</span>
        </button>
        <button class="workflow" data-workflow="W2">
          <strong>W2 个案信息整理</strong>
          <span>按 BPS 和风险边界整理背景信息</span>
        </button>
        <button class="workflow" data-workflow="W3">
          <strong>W3 Session 记录</strong>
          <span>总结单次咨询并生成记录</span>
        </button>
      </aside>

      <section class="result-area" aria-label="结果观察区">
        <div class="tabs" role="tablist">
          <button class="tab active" data-tab="markdown">模型输出</button>
          <button class="tab" data-tab="json">结构化 JSON</button>
          <button class="tab" data-tab="checks">校验结果</button>
        </div>
        <pre id="markdownPane" class="pane active">运行后显示模型输出。</pre>
        <pre id="jsonPane" class="pane">运行后显示结构化 JSON。</pre>
        <pre id="checksPane" class="pane">运行后显示校验结果。</pre>
      </section>

      <aside class="template-panel" aria-label="模板填充">
        <h2>模板填充</h2>
        <label>
          Word 模板路径
          <input id="templatePath" type="text" placeholder="C:\Users\win\Desktop\template.docx" />
        </label>
        <button id="fillTemplateButton" disabled>填充模板</button>
        <div class="path-list">
          <p><strong>输出文件</strong><span id="filledTemplatePath">无</span></p>
          <p><strong>填充报告</strong><span id="templateReportPath">无</span></p>
        </div>
        <pre id="templateReport">需要先运行结构化输出。</pre>
      </aside>

      <section class="input-panel" aria-label="输入与运行控制">
        <textarea id="inputText" placeholder="输入咨询师材料、笔记或需要生成的表单要求"></textarea>
        <div class="controls">
          <label><input id="structuredToggle" type="checkbox" checked /> 结构化输出</label>
          <label><input id="docxToggle" type="checkbox" /> 生成固定 Word</label>
          <label><input id="dryRunToggle" type="checkbox" /> Dry run</label>
          <button id="runButton">运行</button>
        </div>
        <div class="path-list">
          <p><strong>Run 目录</strong><span id="runDir">无</span></p>
          <p><strong>固定 Word</strong><span id="docxPath">无</span></p>
        </div>
      </section>
    </main>
    <script src="/app.js"></script>
  </body>
</html>
```

- [ ] **Step 2: Create CSS layout**

Create `web-workbench/styles.css`:

```css
:root {
  color-scheme: light;
  --bg: #f6f7f9;
  --panel: #ffffff;
  --line: #d8dde6;
  --text: #1f2933;
  --muted: #637083;
  --accent: #2563eb;
  --danger: #b42318;
  --ok: #067647;
}

* { box-sizing: border-box; }

body {
  margin: 0;
  font-family: "Microsoft YaHei", "Segoe UI", Arial, sans-serif;
  color: var(--text);
  background: var(--bg);
}

button, input, textarea {
  font: inherit;
}

.workbench {
  min-height: 100vh;
  display: grid;
  grid-template-columns: 260px minmax(420px, 1fr) 320px;
  grid-template-rows: minmax(0, 1fr) 260px;
  gap: 12px;
  padding: 12px;
}

.workflow-rail,
.result-area,
.template-panel,
.input-panel {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 8px;
}

.workflow-rail {
  grid-row: 1 / span 2;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.brand {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 8px;
}

.brand h1 {
  font-size: 20px;
  margin: 0;
}

.status {
  border: 1px solid var(--line);
  border-radius: 999px;
  padding: 4px 8px;
  font-size: 12px;
  white-space: nowrap;
}

.status.success { color: var(--ok); border-color: #9ad4b5; }
.status.error { color: var(--danger); border-color: #f2a7a0; }

.workflow {
  text-align: left;
  border: 1px solid var(--line);
  background: #fff;
  border-radius: 8px;
  padding: 12px;
  cursor: pointer;
}

.workflow.active {
  border-color: var(--accent);
  box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.12);
}

.workflow span {
  display: block;
  color: var(--muted);
  font-size: 13px;
  margin-top: 6px;
  line-height: 1.35;
}

.result-area {
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.tabs {
  display: flex;
  gap: 8px;
  border-bottom: 1px solid var(--line);
  padding: 10px;
}

.tab {
  border: 1px solid var(--line);
  border-radius: 6px;
  background: #fff;
  padding: 7px 12px;
  cursor: pointer;
}

.tab.active {
  color: #fff;
  border-color: var(--accent);
  background: var(--accent);
}

.pane {
  display: none;
  margin: 0;
  padding: 16px;
  overflow: auto;
  white-space: pre-wrap;
  line-height: 1.55;
  min-height: 0;
  flex: 1;
}

.pane.active { display: block; }

.template-panel {
  grid-row: 1 / span 2;
  padding: 14px;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.template-panel h2 {
  margin: 0;
  font-size: 18px;
}

.template-panel label {
  display: grid;
  gap: 6px;
  color: var(--muted);
  font-size: 13px;
}

.template-panel input {
  border: 1px solid var(--line);
  border-radius: 6px;
  padding: 8px;
  width: 100%;
}

#fillTemplateButton,
#runButton {
  border: 0;
  border-radius: 6px;
  background: var(--accent);
  color: #fff;
  padding: 9px 14px;
  cursor: pointer;
}

#fillTemplateButton:disabled {
  background: #a7b0bf;
  cursor: not-allowed;
}

#templateReport {
  min-height: 0;
  flex: 1;
  overflow: auto;
  border: 1px solid var(--line);
  border-radius: 6px;
  padding: 10px;
  white-space: pre-wrap;
  margin: 0;
}

.input-panel {
  padding: 12px;
  display: grid;
  grid-template-columns: minmax(320px, 1fr) 360px;
  gap: 12px;
}

#inputText {
  resize: none;
  min-height: 220px;
  border: 1px solid var(--line);
  border-radius: 6px;
  padding: 10px;
}

.controls {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 10px;
}

.path-list {
  color: var(--muted);
  font-size: 13px;
  display: grid;
  gap: 8px;
}

.path-list p {
  margin: 0;
}

.path-list span {
  display: block;
  color: var(--text);
  overflow-wrap: anywhere;
  margin-top: 3px;
}

@media (max-width: 980px) {
  .workbench {
    grid-template-columns: 1fr;
    grid-template-rows: auto minmax(360px, 1fr) auto auto;
  }

  .workflow-rail,
  .template-panel {
    grid-row: auto;
  }

  .input-panel {
    grid-template-columns: 1fr;
  }
}
```

- [ ] **Step 3: Create JavaScript behavior**

Create `web-workbench/app.js`:

```javascript
const state = {
  workflow: "W1",
  runDir: null,
  structuredOutput: null,
};

const $ = (id) => document.getElementById(id);

function pretty(value) {
  if (value === null || value === undefined || value === "") return "无";
  if (typeof value === "string") return value;
  return JSON.stringify(value, null, 2);
}

function setStatus(text, kind = "idle") {
  const el = $("runStatus");
  el.textContent = text;
  el.className = `status ${kind}`;
}

function setPane(tabName) {
  document.querySelectorAll(".tab").forEach((tab) => tab.classList.toggle("active", tab.dataset.tab === tabName));
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
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.message || "请求失败");
  }
  return data;
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
  $("fillTemplateButton").disabled = !state.runDir || !state.structuredOutput;
}

async function runAgent(dryRunOverride = null) {
  const input = $("inputText").value.trim();
  if (!input) {
    setStatus("缺少输入", "error");
    return;
  }
  setStatus("运行中", "idle");
  $("runButton").disabled = true;
  try {
    const data = await postJson("/api/run", {
      workflow: state.workflow,
      input,
      structured: $("structuredToggle").checked,
      render_docx: $("docxToggle").checked,
      dry_run: dryRunOverride === null ? $("dryRunToggle").checked : dryRunOverride,
    });
    updateRunResult(data);
    setStatus(data.status === "success" ? "成功" : data.status, data.status === "error" ? "error" : "success");
  } catch (error) {
    setStatus("失败", "error");
    $("checksPane").textContent = error.message;
    setPane("checks");
  } finally {
    $("runButton").disabled = false;
  }
}

async function fillTemplate() {
  const templatePath = $("templatePath").value.trim();
  if (!state.runDir || !state.structuredOutput) {
    $("templateReport").textContent = "需要先运行并获得结构化 JSON。";
    return;
  }
  if (!templatePath) {
    $("templateReport").textContent = "请输入 Word 模板路径。";
    return;
  }
  $("fillTemplateButton").disabled = true;
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
    $("fillTemplateButton").disabled = !state.runDir || !state.structuredOutput;
  }
}

document.querySelectorAll(".workflow").forEach((button) => {
  button.addEventListener("click", () => {
    state.workflow = button.dataset.workflow;
    document.querySelectorAll(".workflow").forEach((item) => item.classList.remove("active"));
    button.classList.add("active");
  });
});

document.querySelectorAll(".tab").forEach((button) => {
  button.addEventListener("click", () => setPane(button.dataset.tab));
});

$("runButton").addEventListener("click", () => runAgent());
$("fillTemplateButton").addEventListener("click", fillTemplate);
```

- [ ] **Step 4: Start server and inspect page manually**

Run:

```powershell
python scripts\web_workbench.py --port 8765
```

Open:

```text
http://127.0.0.1:8765
```

Expected: one workbench screen with left workflow rail, center tabs, bottom input controls, and right template panel. No text overlaps at desktop width. At narrow width, panels stack vertically.

- [ ] **Step 5: Commit**

Run:

```powershell
git add web-workbench/index.html web-workbench/styles.css web-workbench/app.js
git commit -m "Add local workbench UI"
```

---

### Task 6: Add Startup Wrapper And README Notes

**Files:**
- Create: `scripts/run-web-workbench.ps1`
- Modify: `README.md`

- [ ] **Step 1: Create PowerShell wrapper**

Create `scripts/run-web-workbench.ps1`:

```powershell
param(
  [string]$HostName = "127.0.0.1",
  [int]$Port = 8765
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = Split-Path -Parent $ScriptDir

Set-Location $Root
python scripts\web_workbench.py --host $HostName --port $Port
```

- [ ] **Step 2: Add README section**

Add this section to `README.md`:

    ## Local Web Workbench

    Start the local counselor-agent workbench:

        powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run-web-workbench.ps1

    Open:

        http://127.0.0.1:8765

    The workbench can:

    - run W1/W2/W3 with counselor-provided text.
    - show Markdown output, structured JSON, and validation/check results.
    - render a fixed `output.docx` when structured output is available.
    - fill a counselor-provided `.docx` template from the current structured JSON.

    Generated run files are saved under `agent-runs/`, which is ignored by git because it may contain sensitive material. The `.env` API key is never displayed by the workbench.

- [ ] **Step 3: Run wrapper smoke command**

Run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run-web-workbench.ps1 -Port 8765
```

Expected: terminal prints `Workbench running at http://127.0.0.1:8765`. Stop the server with `Ctrl+C` after confirming.

- [ ] **Step 4: Commit**

Run:

```powershell
git add scripts/run-web-workbench.ps1 README.md
git commit -m "Document local web workbench startup"
```

---

### Task 7: End-To-End Verification

**Files:**
- Modify only if verification reveals defects:
  - `scripts/web_workbench.py`
  - `web-workbench/index.html`
  - `web-workbench/styles.css`
  - `web-workbench/app.js`
  - `scripts/test_web_workbench.py`

- [ ] **Step 1: Run full Python test suite**

Run:

```powershell
python -m unittest discover -s scripts -p "test_*.py"
```

Expected: all tests pass.

- [ ] **Step 2: Start local server**

Run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run-web-workbench.ps1 -Port 8765
```

Expected: `Workbench running at http://127.0.0.1:8765`.

- [ ] **Step 3: Browser smoke test**

Open:

```text
http://127.0.0.1:8765
```

Expected:

- Left rail shows W1/W2/W3.
- Center tabs switch between model output, JSON, and checks.
- Bottom textarea and toggles are visible.
- Right template panel is disabled until structured JSON exists.
- No overlapping text at normal desktop size.

- [ ] **Step 4: Dry-run UI test**

In the browser:

- Select W1.
- Enter `请生成初访信息收集表。`
- Keep `结构化输出` checked.
- Check `Dry run`.
- Click `运行`.

Expected:

- Run status becomes success or dry_run.
- Run directory is shown.
- No API key is displayed.
- If no model output exists because dry-run only builds a prompt package, checks pane shows metadata instead of crashing.

- [ ] **Step 5: Real model smoke test**

Only run this if `.env` contains a valid DeepSeek key:

- Uncheck `Dry run`.
- Keep W1 selected.
- Use sample input: `请生成初访前咨询师需要询问的信息收集表。`
- Click `运行`.

Expected:

- Markdown output appears.
- Structured JSON appears.
- Check pane shows structured validation status.
- If fixed Word is enabled, `output.docx` appears under the latest run directory.

- [ ] **Step 6: Final commit if fixes were needed**

If verification required changes, commit them:

```powershell
git add scripts/web_workbench.py scripts/test_web_workbench.py web-workbench/index.html web-workbench/styles.css web-workbench/app.js README.md
git commit -m "Stabilize local workbench"
```

If no changes were needed, do not create an empty commit.

---

## Self-Review

Spec coverage:

- Local browser workbench: Task 1 and Task 5.
- Explicit W1/W2/W3 selection: Task 5.
- Text input and run controls: Task 5.
- Structured output and fixed DOCX toggles: Task 2 and Task 5.
- Markdown/JSON/check display: Task 2 and Task 5.
- Template fill panel: Task 3 and Task 5.
- Output paths: Task 2, Task 3, and Task 5.
- Error handling: Task 2, Task 3, and Task 5.
- File path safety: Task 4.
- Startup command and docs: Task 6.
- Tests and verification: Tasks 1 through 4 and Task 7.

Scope check:

- This plan intentionally avoids login, deployment, case database, audio transcription, multi-turn memory, and React/Next.js.
- It uses the existing script pipeline and keeps generated files under `agent-runs/`.

Type and naming consistency:

- API paths are `/api/run`, `/api/render-docx`, `/api/fill-template`, and `/files/<path>`.
- Response fields match the design document: `status`, `workflow`, `run_dir`, `clean_output`, `structured_output`, `structured_check`, `docx`, `issues`.
- Template fill uses `filled_template.docx` and `template_fill_report.json`.
