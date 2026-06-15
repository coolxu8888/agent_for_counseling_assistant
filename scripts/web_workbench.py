import argparse
import json
import mimetypes
import sys
import zipfile
from datetime import datetime, timezone
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote, unquote, urlparse


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from run_agent import AgentInputError, AgentRunResult, create_run_dir, run_agent_once
from fill_docx_template import (
    extract_template_slots,
    fill_docx_template,
    fill_docx_template_from_raw,
    is_placeholder_text,
)
from render_docx import render_docx
from workbench_store import WorkbenchStore


ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = ROOT / "web-workbench"
RUN_ROOT = ROOT / "agent-runs"
DATA_ROOT = ROOT / "workbench-data"
UPLOAD_ROOT = DATA_ROOT / "uploads"
DB_PATH = DATA_ROOT / "workbench.sqlite3"
ICON_PATH = ROOT / "Gemini_Generated_Image_agent图标.png"
RUN_LOG_PATH = ROOT / "workbench-run-log.jsonl"
SESSION_COOKIE = "workbench_session"
STORE = WorkbenchStore(DB_PATH, UPLOAD_ROOT)

AGENT_STYLE_INSTRUCTIONS = {
    "default": "",
    "professional_concise": "请使用专业、简洁、清晰的咨询记录语言输出。",
    "warm_clinical": "请使用温和、支持性、但仍保持专业边界的临床语言输出。",
    "institutional_record": "请使用正式、克制、适合机构留档的记录语言输出。",
    "supervision_summary": "请使用适合督导讨论的语言输出，突出事实、假设、风险边界和后续工作重点。",
    "custom": "",
}


def detect_workflow(user_input):
    text = str(user_input or "").lower()
    if any(keyword in text for keyword in ["soap", "dap", "birp", "session", "本次咨询", "下次咨询", "咨询记录", "风险变化"]):
        return "W3"
    if any(keyword in text for keyword in ["个案概念化", "个案信息", "个案背景", "bps", "biopsychosocial", "督导", "去识别"]):
        return "W2"
    if any(keyword in text for keyword in ["初访", "初始访谈", "信息收集", "访谈表", "收集表", "来访信息"]):
        return "W1"
    if any(keyword in text for keyword in ["记录", "总结", "干预", "来访者反应", "下次"]):
        return "W3"
    return "W2"


def append_run_log(action, user_id=None, case_id=None, details=None):
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "action": action,
        "user_id": user_id,
        "case_id": case_id,
        "details": details or {},
    }
    with RUN_LOG_PATH.open("a", encoding="utf-8") as log_file:
        log_file.write(json.dumps(entry, ensure_ascii=False) + "\n")


def json_response(payload, status=200):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {"Content-Type": "application/json; charset=utf-8"}
    return status, headers, body


def json_response_with_headers(payload, extra_headers, status=200):
    response_status, headers, body = json_response(payload, status=status)
    headers.update(extra_headers)
    return response_status, headers, body


def error_response(status, message, issues=None):
    payload = {"status": "error", "message": message}
    if issues is not None:
        payload["issues"] = issues
    return json_response(payload, status=status)


def cookie_header(token, max_age=604800):
    return (
        f"{SESSION_COOKIE}={token}; Path=/; Max-Age={max_age}; "
        "HttpOnly; SameSite=Lax"
    )


def clear_cookie_header():
    return f"{SESSION_COOKIE}=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax"


def cookie_token(handler):
    cookie = SimpleCookie(handler.headers.get("Cookie", ""))
    morsel = cookie.get(SESSION_COOKIE)
    return morsel.value if morsel else ""


def current_user(handler):
    return STORE.session_user(cookie_token(handler))


def require_user(handler):
    user = current_user(handler)
    if not user:
        return None, error_response(401, "Login required.")
    return user, None


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


def is_relative_to(path, root):
    path = Path(path).resolve()
    root = Path(root).resolve()
    return path == root or root in path.parents


def require_run_file(run_dir_value, filename):
    run_dir = Path(str(run_dir_value)).resolve()
    if not run_dir.is_dir():
        raise FileNotFoundError("Run directory not found.")
    if not is_relative_to(run_dir, RUN_ROOT):
        raise PermissionError("Run directory is outside approved output directory.")
    target = run_dir / filename
    if not target.exists():
        raise FileNotFoundError(f"{filename} not found in run directory.")
    return run_dir, target


def optional_run_dir(run_dir_value, workflow_id="TEMPLATE"):
    if run_dir_value:
        run_dir = Path(str(run_dir_value)).resolve()
        if not run_dir.is_dir():
            raise FileNotFoundError("Run directory not found.")
        if not is_relative_to(run_dir, RUN_ROOT):
            raise PermissionError("Run directory is outside approved output directory.")
        return run_dir
    return create_run_dir(run_root=RUN_ROOT, workflow_id=workflow_id)


def apply_output_style(user_input, style="default", custom_style=""):
    style = style if style in AGENT_STYLE_INSTRUCTIONS else "default"
    instruction = custom_style.strip() if style == "custom" else AGENT_STYLE_INSTRUCTIONS[style]
    if not instruction:
        return user_input
    return f"{user_input.strip()}\n\n输出风格要求：{instruction}"


def resolve_download_path(path_value, allowed_roots=None):
    allowed_roots = allowed_roots or [RUN_ROOT]
    candidate = Path(str(path_value)).resolve()
    if not candidate.is_file():
        raise FileNotFoundError(str(candidate))
    if not any(is_relative_to(candidate, root) for root in allowed_roots):
        raise ValueError("Download path is outside approved output directories.")
    return candidate


def safe_content_disposition(filename):
    cleaned = "".join(
        ch if 32 <= ord(ch) < 127 and ch not in {'"', "\\", ";"} else "_"
        for ch in filename
    )
    cleaned = cleaned or "download"
    encoded = quote(filename, safe="")
    return f"attachment; filename=\"{cleaned}\"; filename*=UTF-8''{encoded}"


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
    requested_workflow = str(payload.get("workflow") or "AUTO")
    user_input = payload.get("input", "")
    if not str(user_input).strip():
        return error_response(400, "Input is required.")
    workflow = detect_workflow(user_input) if requested_workflow == "AUTO" else requested_workflow
    user_input = apply_output_style(
        str(user_input),
        style=str(payload.get("output_style") or "default"),
        custom_style=str(payload.get("custom_output_style") or ""),
    )

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
        case_id = payload.get("case_id")
        if payload.get("user_id"):
            user_id = int(payload["user_id"])
            resolved_case_id = int(case_id) if case_id else None
            STORE.audit(
                user_id,
                resolved_case_id,
                "workflow.run",
                {
                    "workflow": workflow,
                    "requested_workflow": requested_workflow,
                    "run_dir": path_for_ui(result.run_dir),
                },
            )
            append_run_log(
                "workflow.run",
                user_id=user_id,
                case_id=resolved_case_id,
                details={
                    "workflow": workflow,
                    "requested_workflow": requested_workflow,
                    "status": result.status,
                    "run_dir": path_for_ui(result.run_dir),
                    "structured": structured or render_docx,
                    "render_docx": render_docx,
                    "dry_run": dry_run,
                },
            )
        response_payload = load_run_payload(result)
        response_payload["detected_workflow"] = workflow
        response_payload["requested_workflow"] = requested_workflow
        return json_response(response_payload)
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
    except (FileNotFoundError, PermissionError, ValueError) as exc:
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
    except (FileNotFoundError, PermissionError, ValueError) as exc:
        return error_response(400, str(exc))
    except Exception as exc:
        print(f"Template fill failed: {exc}")
        return error_response(500, "Template fill failed.")


def summarize_template_slots(slots):
    fillable_slots = [
        slot
        for slot in slots
        if is_placeholder_text(slot.get("current_text", ""))
        or slot.get("slot_type") == "table_block_cell"
    ]
    prefilled_slots = [
        slot
        for slot in slots
        if not is_placeholder_text(slot.get("current_text", ""))
        and slot.get("slot_type") != "table_block_cell"
    ]
    return {
        "total_slots": len(slots),
        "fillable_slots": len(fillable_slots),
        "prefilled_slots": len(prefilled_slots),
        "slot_types": {
            slot_type: sum(1 for slot in slots if slot.get("slot_type") == slot_type)
            for slot_type in sorted({slot.get("slot_type", "unknown") for slot in slots})
        },
    }


def handle_inspect_template(payload):
    try:
        template_path = Path(str(payload.get("template_path"))).resolve()
        if not template_path.exists():
            return error_response(400, "Template file not found.")
        slots = extract_template_slots(template_path, include_prefilled=True)
        return json_response(
            {
                "status": "success",
                "template_path": path_for_ui(template_path),
                "summary": summarize_template_slots(slots),
                "slots": slots,
            }
        )
    except (FileNotFoundError, PermissionError, ValueError, zipfile.BadZipFile) as exc:
        return error_response(400, str(exc))
    except Exception as exc:
        print(f"Template inspect failed: {exc}")
        return error_response(500, "Template inspect failed.")


def handle_draft_template(payload):
    try:
        template_path = Path(str(payload.get("template_path"))).resolve()
        if not template_path.exists():
            return error_response(400, "Template file not found.")
        raw_input = str(payload.get("raw_input") or "").strip()
        if not raw_input:
            return error_response(400, "Raw input is required.")

        run_dir = optional_run_dir(payload.get("run_dir"), workflow_id="TEMPLATE")
        output_path = run_dir / "filled_template.docx"
        draft_path = run_dir / "template_draft.json"
        report_path = run_dir / "template_fill_report.json"
        report = fill_docx_template_from_raw(
            template_path,
            raw_input,
            output_path,
            report_path,
            draft_path,
            style=str(payload.get("style") or "professional_concise"),
            custom_style=str(payload.get("custom_style") or ""),
            existing_content_policy=str(payload.get("existing_content_policy") or "merge"),
        )
        case_id = payload.get("case_id")
        if payload.get("user_id"):
            user_id = int(payload["user_id"])
            resolved_case_id = int(case_id) if case_id else None
            STORE.audit(
                user_id,
                resolved_case_id,
                "template.draft",
                {"template_path": str(template_path), "run_dir": path_for_ui(run_dir)},
            )
            append_run_log(
                "template.draft",
                user_id=user_id,
                case_id=resolved_case_id,
                details={
                    "template_path": str(template_path),
                    "run_dir": path_for_ui(run_dir),
                    "status": report.get("status"),
                    "output_path": path_for_ui(output_path) if output_path.exists() else None,
                    "report_path": path_for_ui(report_path),
                },
            )
        status = "success" if report.get("status") != "FAIL" else "error"
        return json_response(
            {
                "status": status,
                "run_dir": path_for_ui(run_dir),
                "output_path": path_for_ui(output_path) if output_path.exists() else None,
                "draft_path": path_for_ui(draft_path) if draft_path.exists() else None,
                "report_path": path_for_ui(report_path),
                "report": report,
            },
            status=200 if status == "success" else 500,
        )
    except (FileNotFoundError, PermissionError, ValueError) as exc:
        return error_response(400, str(exc))
    except Exception as exc:
        print(f"Template draft failed: {exc}")
        return error_response(500, "Template draft failed.")


def handle_login(payload):
    username = str(payload.get("username") or "").strip()
    password = str(payload.get("password") or "")
    auth = STORE.authenticate(username, password)
    if not auth:
        return error_response(401, "Invalid username or password.")
    STORE.audit(auth["user"]["id"], None, "auth.login", {"username": username})
    append_run_log("auth.login", user_id=auth["user"]["id"], details={"username": username})
    return json_response_with_headers(
        {"status": "success", "user": auth["user"], "expires_at": auth["expires_at"]},
        {"Set-Cookie": cookie_header(auth["token"])},
    )


def handle_logout(handler):
    token = cookie_token(handler)
    user = STORE.session_user(token)
    if user:
        STORE.audit(user["id"], None, "auth.logout", {})
        append_run_log("auth.logout", user_id=user["id"])
    STORE.logout(token)
    return json_response_with_headers(
        {"status": "success"},
        {"Set-Cookie": clear_cookie_header()},
    )


def handle_session(handler):
    user = current_user(handler)
    return json_response({"status": "success", "user": user, "authenticated": bool(user)})


def handle_cases(user, payload=None):
    payload = payload or {}
    if payload.get("action") == "create":
        case_record = STORE.create_case(
            user["id"],
            str(payload.get("title") or "未命名个案"),
            client_code=str(payload.get("client_code") or ""),
            notes=str(payload.get("notes") or ""),
        )
        append_run_log(
            "case.create",
            user_id=user["id"],
            case_id=case_record["id"],
            details={"title": case_record["title"], "client_code": case_record["client_code"]},
        )
        return json_response({"status": "success", "case": case_record})
    if payload.get("action") == "update":
        case_id = int(payload.get("case_id") or 0)
        case_record = STORE.update_case(
            user["id"],
            case_id,
            title=payload.get("title"),
            client_code=payload.get("client_code"),
            notes=payload.get("notes"),
        )
        if not case_record:
            return error_response(404, "Case not found.")
        append_run_log(
            "case.update",
            user_id=user["id"],
            case_id=case_record["id"],
            details={"title": case_record["title"], "client_code": case_record["client_code"]},
        )
        return json_response({"status": "success", "case": case_record})
    return json_response({"status": "success", "cases": STORE.list_cases(user["id"])})


def handle_upload(user, payload):
    filename = str(payload.get("filename") or "").strip()
    content_b64 = str(payload.get("content_base64") or "")
    if not filename or not content_b64:
        return error_response(400, "filename and content_base64 are required.")
    case_id = payload.get("case_id")
    upload = STORE.store_upload(
        user["id"],
        filename,
        content_b64,
        content_type=str(payload.get("content_type") or ""),
        case_id=int(case_id) if case_id else None,
    )
    append_run_log(
        "file.upload",
        user_id=user["id"],
        case_id=int(case_id) if case_id else None,
        details={
            "original_name": upload["original_name"],
            "stored_path": upload["stored_path"],
            "size_bytes": upload["size_bytes"],
            "content_type": upload["content_type"],
        },
    )
    return json_response({"status": "success", "upload": upload})


def handle_uploads(user, payload=None):
    payload = payload or {}
    case_id = payload.get("case_id")
    return json_response(
        {
            "status": "success",
            "uploads": STORE.list_uploads(user["id"], case_id=int(case_id) if case_id else None),
        }
    )


def handle_audit_logs(user):
    return json_response({"status": "success", "audit_logs": STORE.list_audit_logs(user["id"])})


def resolve_static_path(request_path, web_root=WEB_ROOT):
    parsed_path = unquote(urlparse(request_path).path)
    if parsed_path == "/agent-icon.png" and ICON_PATH.exists():
        return ICON_PATH
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
            "Content-Disposition": safe_content_disposition(target.name),
        },
        body,
    )


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
        path = urlparse(self.path).path
        if path == "/health":
            send_response_tuple(self, json_response({"status": "ok"}))
            return
        if path == "/api/session":
            send_response_tuple(self, handle_session(self))
            return

        if self.path.startswith("/files/"):
            user, error = require_user(self)
            if error:
                send_response_tuple(self, error)
                return
            try:
                response = handle_file_download(self.path)
            except FileNotFoundError:
                response = error_response(404, "Download file not found.")
            except Exception as exc:
                response = error_response(400, str(exc))
            send_response_tuple(self, response)
            return

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
        if path == "/api/login":
            response = handle_login(payload)
            send_response_tuple(self, response)
            return
        if path == "/api/logout":
            response = handle_logout(self)
            send_response_tuple(self, response)
            return

        user, error = require_user(self)
        if error:
            send_response_tuple(self, error)
            return

        if isinstance(payload, dict):
            payload["user_id"] = user["id"]

        if path == "/api/run":
            response = handle_api_run(payload)
        elif path == "/api/render-docx":
            response = handle_render_docx(payload)
        elif path == "/api/fill-template":
            response = handle_fill_template(payload)
        elif path == "/api/inspect-template":
            response = handle_inspect_template(payload)
        elif path == "/api/draft-template":
            response = handle_draft_template(payload)
        elif path == "/api/cases":
            response = handle_cases(user, payload)
        elif path == "/api/uploads":
            response = handle_uploads(user, payload)
        elif path == "/api/upload":
            response = handle_upload(user, payload)
        elif path == "/api/audit":
            response = handle_audit_logs(user)
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
