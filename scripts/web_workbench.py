import argparse
import json
import mimetypes
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from run_agent import AgentInputError, AgentRunResult, run_agent_once
from fill_docx_template import fill_docx_template
from render_docx import render_docx


ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = ROOT / "web-workbench"
RUN_ROOT = ROOT / "agent-runs"


def json_response(payload, status=200):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {"Content-Type": "application/json; charset=utf-8"}
    return status, headers, body


def error_response(status, message, issues=None):
    payload = {"status": "error", "message": message}
    if issues is not None:
        payload["issues"] = issues
    return json_response(payload, status=status)


def read_text_if_exists(path):
    return path.read_text(encoding="utf-8") if path.exists() else ""


def read_json_artifact(path, issues):
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        issues.append(
            {
                "level": "WARN",
                "path": path_for_ui(path),
                "message": f"Could not parse JSON artifact: {path.name}",
            }
        )
        return None


def path_for_ui(path):
    return str(path.resolve())


def require_run_file(run_dir_value, filename):
    run_dir = Path(str(run_dir_value)).resolve()
    target = run_dir / filename
    if not target.exists():
        raise FileNotFoundError(f"{filename} not found in run directory.")
    return run_dir, target


def load_run_payload(result):
    run_dir = result.run_dir
    issues = []
    structured_output = read_json_artifact(run_dir / "structured_output.json", issues)
    structured_check = read_json_artifact(run_dir / "structured_check.json", issues)
    safety_check = read_json_artifact(run_dir / "safety_check.json", issues)
    metadata = read_json_artifact(run_dir / "metadata.json", issues)
    docx_check = read_json_artifact(run_dir / "docx_check.json", issues)
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
            "status": (
                docx_check["status"]
                if isinstance(docx_check, dict) and "status" in docx_check
                else "skipped"
            ),
            "path": path_for_ui(docx_path) if docx_path.exists() else None,
            "check": docx_check,
        },
        "issues": issues,
    }


def handle_api_run(payload):
    workflow = payload.get("workflow", "W1")
    user_input = payload.get("input", "")
    if not str(user_input).strip():
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
    except AgentInputError as exc:
        return error_response(400, str(exc))
    except Exception as exc:
        print(f"Agent run failed: {exc}")
        return error_response(500, "Agent run failed.")


def handle_render_docx(payload):
    try:
        run_dir, structured_path = require_run_file(payload.get("run_dir"), "structured_output.json")
        data = json.loads(structured_path.read_text(encoding="utf-8"))
        output_path = run_dir / "output.docx"
        check_path = run_dir / "docx_check.json"
        check = render_docx(data, output_path)
        check_path.write_text(json.dumps(check, ensure_ascii=False, indent=2), encoding="utf-8")
        status = "success" if check.get("status") != "FAIL" else "error"
        return json_response(
            {
                "status": status,
                "output_path": path_for_ui(output_path) if output_path.exists() else None,
                "check_path": path_for_ui(check_path),
                "check": check,
            },
            status=200 if status == "success" else 500,
        )
    except FileNotFoundError as exc:
        return error_response(400, str(exc))
    except Exception as exc:
        print(f"DOCX render failed: {exc}")
        return error_response(500, "DOCX render failed.")


def handle_fill_template(payload):
    try:
        run_dir, structured_path = require_run_file(payload.get("run_dir"), "structured_output.json")
        template_path = Path(str(payload.get("template_path"))).resolve()
        if not template_path.exists():
            return error_response(400, "Template file not found.")

        output_path = run_dir / "filled_template.docx"
        report_path = run_dir / "template_fill_report.json"
        report = fill_docx_template(template_path, structured_path, output_path, report_path)
        status = "success" if report.get("status") != "FAIL" else "error"
        return json_response(
            {
                "status": status,
                "output_path": path_for_ui(output_path) if output_path.exists() else None,
                "report_path": path_for_ui(report_path),
                "report": report,
            },
            status=200 if status == "success" else 500,
        )
    except FileNotFoundError as exc:
        return error_response(400, str(exc))
    except Exception as exc:
        print(f"Template fill failed: {exc}")
        return error_response(500, "Template fill failed.")


def resolve_static_path(request_path, web_root=WEB_ROOT):
    parsed_path = unquote(urlparse(request_path).path)
    if parsed_path == "/":
        parsed_path = "/index.html"

    relative_path = parsed_path.lstrip("/")
    resolved_root = web_root.resolve()
    resolved_path = (resolved_root / relative_path).resolve()

    if resolved_path != resolved_root and resolved_root not in resolved_path.parents:
        raise ValueError("Static path is outside web root.")
    if not resolved_path.is_file():
        raise FileNotFoundError(resolved_path)

    return resolved_path


def read_json_body(handler):
    content_length = int(handler.headers.get("Content-Length", "0") or "0")
    if content_length <= 0:
        return {}

    body = handler.rfile.read(content_length)
    return json.loads(body.decode("utf-8"))


def send_response_tuple(handler, response):
    status, headers, body = response
    handler.send_response(status)
    for name, value in headers.items():
        handler.send_header(name, value)
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


class WorkbenchHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            static_path = resolve_static_path(self.path)
            content_type = mimetypes.guess_type(static_path.name)[0] or "application/octet-stream"
            body = static_path.read_bytes()
            response = 200, {"Content-Type": content_type}, body
        except FileNotFoundError:
            response = error_response(404, "Static file not found.")
        except Exception as exc:
            response = error_response(400, str(exc))

        send_response_tuple(self, response)

    def do_POST(self):
        try:
            payload = read_json_body(self)
        except json.JSONDecodeError:
            send_response_tuple(self, error_response(400, "Invalid JSON request."))
            return

        path = urlparse(self.path).path
        if path == "/api/run":
            response = handle_api_run(payload)
        elif path == "/api/render-docx":
            response = handle_render_docx(payload)
        elif path == "/api/fill-template":
            response = handle_fill_template(payload)
        else:
            response = error_response(404, "Endpoint not found.")

        send_response_tuple(self, response)


def create_server(host="127.0.0.1", port=8765):
    return ThreadingHTTPServer((host, port), WorkbenchHandler)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Run the local web workbench server.")
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
