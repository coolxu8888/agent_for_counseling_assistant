import argparse
import base64
import binascii
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote, urlparse


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from web_workbench import (
    RUN_ROOT,
    error_response,
    handle_api_run,
    handle_draft_template,
    json_response,
    read_json_body,
    send_response_tuple,
)
from run_agent import create_run_dir


ROOT = Path(__file__).resolve().parents[1]
OPENAPI_PATH = ROOT / "docs" / "coze-openapi.json"
MAX_TEMPLATE_BYTES = 10 * 1024 * 1024


def response_payload(response):
    status, _headers, body = response
    try:
        payload = json.loads(body.decode("utf-8"))
    except Exception:
        payload = {"status": "error", "message": "Invalid JSON response from backend."}
    return status, payload


def request_base_url(handler):
    proto = handler.headers.get("X-Forwarded-Proto", "http")
    host = handler.headers.get("X-Forwarded-Host") or handler.headers.get("Host")
    return f"{proto}://{host}" if host else ""


def artifact_url(handler, path):
    if not path:
        return None
    base_url = request_base_url(handler)
    return f"{base_url}/files/{quote(str(path), safe='')}" if base_url else None


def artifact_item(handler, name, path, kind):
    if not path:
        return None
    return {
        "name": name,
        "kind": kind,
        "path": path,
        "url": artifact_url(handler, path),
    }


def compact_checks(payload):
    return {
        "structured_check": payload.get("structured_check"),
        "safety_check": payload.get("safety_check"),
        "docx": payload.get("docx"),
        "issues": payload.get("issues", []),
    }


def build_run_workflow_response(handler, backend_payload):
    docx = backend_payload.get("docx") or {}
    artifacts = [
        item
        for item in [
            artifact_item(handler, "output.docx", docx.get("path"), "docx"),
        ]
        if item
    ]
    answer = backend_payload.get("clean_output") or backend_payload.get("raw_output") or ""
    if not answer:
        answer = "已完成工作流运行，但没有生成可读文本输出。"
    return {
        "status": backend_payload.get("status", "success"),
        "answer": answer,
        "workflow": backend_payload.get("workflow"),
        "run_dir": backend_payload.get("run_dir"),
        "artifacts": artifacts,
        "structured_output": backend_payload.get("structured_output"),
        "checks": compact_checks(backend_payload),
    }


def build_draft_template_response(handler, backend_payload):
    artifacts = [
        item
        for item in [
            artifact_item(handler, "filled_template.docx", backend_payload.get("output_path"), "docx"),
            artifact_item(handler, "template_draft.json", backend_payload.get("draft_path"), "json"),
            artifact_item(handler, "template_fill_report.json", backend_payload.get("report_path"), "json"),
        ]
        if item
    ]
    report = backend_payload.get("report") or {}
    filled_count = len(report.get("filled_fields", []))
    kept_count = len(report.get("kept_fields", []))
    skipped_count = len(report.get("skipped_fields", []))
    issue_count = len(report.get("issues", []))
    answer = (
        f"模板填充已完成：填充 {filled_count} 项，保留 {kept_count} 项，"
        f"跳过 {skipped_count} 项，提示 {issue_count} 条。请下载 Word 并查看填充报告。"
    )
    return {
        "status": backend_payload.get("status", "success"),
        "answer": answer,
        "run_dir": backend_payload.get("run_dir"),
        "artifacts": artifacts,
        "report": report,
    }


def handle_coze_run_workflow(payload, handler):
    backend_response = handle_api_run(
        {
            "workflow": payload.get("workflow", "W3"),
            "input": payload.get("input") or payload.get("raw_input") or "",
            "structured": payload.get("structured", True),
            "render_docx": payload.get("render_docx", True),
            "dry_run": payload.get("dry_run", False),
            "output_style": payload.get("output_style", "professional_concise"),
            "custom_output_style": payload.get("custom_output_style", ""),
        }
    )
    status, backend_payload = response_payload(backend_response)
    if status >= 400:
        return json_response(backend_payload, status=status)
    return json_response(build_run_workflow_response(handler, backend_payload))


def handle_coze_draft_template(payload, handler):
    template_path = payload.get("template_path", "")
    run_dir = payload.get("run_dir")
    if payload.get("template_base64"):
        try:
            uploaded_template, run_dir = save_template_base64(
                payload.get("template_base64", ""),
                payload.get("template_filename", "template.docx"),
                run_dir,
            )
            template_path = str(uploaded_template)
        except ValueError as exc:
            return error_response(400, str(exc))

    backend_response = handle_draft_template(
        {
            "template_path": template_path,
            "raw_input": payload.get("raw_input") or payload.get("input") or "",
            "style": payload.get("style", payload.get("output_style", "professional_concise")),
            "custom_style": payload.get("custom_style", payload.get("custom_output_style", "")),
            "existing_content_policy": payload.get("existing_content_policy", "merge"),
            "run_dir": str(run_dir) if run_dir else None,
        }
    )
    status, backend_payload = response_payload(backend_response)
    if status >= 400:
        return json_response(backend_payload, status=status)
    return json_response(build_draft_template_response(handler, backend_payload))


def safe_template_filename(filename):
    name = Path(str(filename or "template.docx")).name
    if not name.lower().endswith(".docx"):
        name = f"{name}.docx"
    return "".join(ch if ch.isalnum() or ch in {".", "-", "_"} else "_" for ch in name) or "template.docx"


def save_template_base64(template_base64, template_filename="template.docx", run_dir=None):
    try:
        raw = base64.b64decode(str(template_base64), validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("template_base64 is not valid base64.") from exc
    if not raw:
        raise ValueError("template_base64 is empty.")
    if len(raw) > MAX_TEMPLATE_BYTES:
        raise ValueError("template_base64 exceeds the 10MB demo limit.")
    target_run_dir = Path(run_dir).resolve() if run_dir else create_run_dir(run_root=RUN_ROOT, workflow_id="COZE-TEMPLATE")
    if target_run_dir != RUN_ROOT.resolve() and RUN_ROOT.resolve() not in target_run_dir.parents:
        raise ValueError("Run directory is outside approved output directory.")
    target_run_dir.mkdir(parents=True, exist_ok=True)
    path = target_run_dir / safe_template_filename(template_filename)
    path.write_bytes(raw)
    return path, target_run_dir


def auth_error():
    return json_response({"status": "error", "message": "Unauthorized."}, status=401)


def is_authorized(handler):
    expected = os.environ.get("COZE_DEMO_API_KEY", "").strip()
    if not expected:
        return True
    header_value = handler.headers.get("Authorization", "")
    api_key_value = handler.headers.get("X-API-Key", "")
    return header_value == f"Bearer {expected}" or api_key_value == expected


def openapi_spec(base_url="https://your-domain.example"):
    api_base_url = f"{base_url.rstrip('/')}/coze"
    artifact_schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "type": {"type": "string"},
            "path": {"type": "string"},
            "url": {"type": "string"},
        },
    }
    workflow_response_schema = {
        "type": "object",
        "properties": {
            "status": {"type": "string"},
            "answer": {"type": "string"},
            "workflow": {"type": "string"},
            "run_dir": {"type": "string"},
            "artifacts": {"type": "array", "items": artifact_schema},
            "structured_output": {"type": "object"},
            "checks": {"type": "object"},
        },
    }
    template_response_schema = {
        "type": "object",
        "properties": {
            "status": {"type": "string"},
            "answer": {"type": "string"},
            "run_dir": {"type": "string"},
            "artifacts": {"type": "array", "items": artifact_schema},
            "report": {"type": "object"},
        },
    }
    return {
        "openapi": "3.0.3",
        "info": {
            "title": "Counselor Assistant Coze Demo API",
            "version": "0.1.0",
            "description": "Coze-facing demo wrapper for counselor assistant workflows.",
        },
        "servers": [{"url": api_base_url}],
        "paths": {
            "/run_workflow": {
                "post": {
                    "summary": "Run a counselor assistant workflow",
                    "operationId": "run_workflow",
                    "security": [{"ApiKeyAuth": []}],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["input"],
                                    "properties": {
                                        "workflow": {"type": "string", "enum": ["W1", "W2", "W3"], "default": "W3"},
                                        "input": {"type": "string"},
                                        "output_style": {
                                            "type": "string",
                                            "enum": [
                                                "default",
                                                "professional_concise",
                                                "warm_clinical",
                                                "institutional_record",
                                                "supervision_summary",
                                                "custom",
                                            ],
                                            "default": "professional_concise",
                                        },
                                        "custom_output_style": {"type": "string"},
                                        "render_docx": {"type": "boolean", "default": True},
                                    },
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {
                            "description": "Workflow result",
                            "content": {"application/json": {"schema": workflow_response_schema}},
                        }
                    },
                }
            },
            "/draft_template": {
                "post": {
                    "summary": "Draft and fill a Word template from raw counselor material",
                    "operationId": "draft_template",
                    "security": [{"ApiKeyAuth": []}],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["raw_input"],
                                    "properties": {
                                        "template_path": {
                                            "type": "string",
                                            "description": "Server-local DOCX path. Use only for local testing or preloaded server templates.",
                                        },
                                        "template_base64": {
                                            "type": "string",
                                            "description": "Base64-encoded .docx template content for deployed demos.",
                                        },
                                        "template_filename": {
                                            "type": "string",
                                            "description": "Original filename for template_base64. Defaults to template.docx.",
                                        },
                                        "raw_input": {"type": "string"},
                                        "style": {
                                            "type": "string",
                                            "enum": [
                                                "professional_concise",
                                                "warm_clinical",
                                                "institutional_record",
                                                "supervision_summary",
                                                "custom",
                                            ],
                                            "default": "professional_concise",
                                        },
                                        "custom_style": {"type": "string"},
                                        "existing_content_policy": {
                                            "type": "string",
                                            "enum": ["merge", "ask", "replace", "blank_only"],
                                            "default": "merge",
                                        },
                                    },
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {
                            "description": "Template fill result",
                            "content": {"application/json": {"schema": template_response_schema}},
                        }
                    },
                }
            },
        },
        "components": {
            "securitySchemes": {
                "ApiKeyAuth": {
                    "type": "apiKey",
                    "in": "header",
                    "name": "X-API-Key",
                }
            }
        },
    }


class CozeApiHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/health":
            send_response_tuple(self, json_response({"status": "ok"}))
            return
        if path == "/openapi.json":
            base_url = request_base_url(self) or "https://your-domain.example"
            send_response_tuple(self, json_response(openapi_spec(base_url=base_url)))
            return
        if path.startswith("/files/"):
            from web_workbench import handle_file_download

            send_response_tuple(self, handle_file_download(self.path))
            return
        send_response_tuple(self, error_response(404, "Endpoint not found."))

    def do_POST(self):
        if not is_authorized(self):
            send_response_tuple(self, auth_error())
            return
        try:
            payload = read_json_body(self)
        except json.JSONDecodeError:
            send_response_tuple(self, error_response(400, "Invalid JSON request."))
            return

        path = urlparse(self.path).path
        if path == "/coze/run_workflow":
            response = handle_coze_run_workflow(payload, self)
        elif path == "/coze/draft_template":
            response = handle_coze_draft_template(payload, self)
        else:
            response = error_response(404, "Endpoint not found.")
        send_response_tuple(self, response)


def create_server(host="127.0.0.1", port=8770):
    return ThreadingHTTPServer((host, port), CozeApiHandler)


def write_openapi(path=OPENAPI_PATH, base_url="https://your-domain.example"):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(openapi_spec(base_url=base_url), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return target


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Run the Coze demo API wrapper.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8770)
    parser.add_argument("--write-openapi", action="store_true")
    parser.add_argument("--base-url", default="https://your-domain.example")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    if args.write_openapi:
        path = write_openapi(base_url=args.base_url)
        print(f"OpenAPI spec written: {path}")
        return 0
    server = create_server(args.host, args.port)
    print(f"Coze demo API running at http://{args.host}:{args.port}")
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
