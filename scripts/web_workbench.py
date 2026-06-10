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

from run_agent import AgentRunResult, run_agent_once


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


def read_json_if_exists(path):
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def path_for_ui(path):
    return str(path.resolve())


def load_run_payload(result):
    run_dir = result.run_dir
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
            "status": (
                docx_check["status"]
                if isinstance(docx_check, dict) and "status" in docx_check
                else "skipped"
            ),
            "path": path_for_ui(docx_path) if docx_path.exists() else None,
            "check": docx_check,
        },
        "issues": [],
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
    except Exception as exc:
        return error_response(500, str(exc))


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
