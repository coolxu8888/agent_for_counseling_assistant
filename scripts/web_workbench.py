import argparse
import base64
import json
import mimetypes
import os
import shutil
import sys
import tempfile
import zipfile
from datetime import datetime, timedelta, timezone
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
from workbench_store import WorkbenchStore, parse_iso, utc_now


ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = ROOT / "web-workbench"
RUN_ROOT = ROOT / "agent-runs"
DATA_ROOT = ROOT / "workbench-data"
UPLOAD_ROOT = DATA_ROOT / "uploads"
DOCS_ROOT = ROOT / "docs"
DB_PATH = DATA_ROOT / "workbench.sqlite3"
ICON_PATH = ROOT / "Gemini_Generated_Image_agent\u56fe\u6807.png"
RUN_LOG_PATH = ROOT / "workbench-run-log.jsonl"
SESSION_COOKIE = "workbench_session"
STORE = WorkbenchStore(DB_PATH, UPLOAD_ROOT)
WORKSPACE_BACKUP_VERSION = 1
RUN_ARTIFACT_FILE_NAMES = {
    "input": "input.json",
    "prompt_package": "prompt_package.txt",
    "metadata": "metadata.json",
    "raw_output": "raw_output.txt",
    "clean_output": "clean_output.md",
    "structured_output": "structured_output.json",
    "structured_check": "structured_check.json",
    "safety_check": "safety_check.json",
    "docx": "output.docx",
    "docx_check": "docx_check.json",
    "filled_template": "filled_template.docx",
    "template_draft": "template_draft.json",
    "template_report": "template_fill_report.json",
}

DEMO_SCENARIOS = [
    {
        "id": "case-family-boundary",
        "title": "Recommended demo: W2 case summary",
        "workflow": "W2",
        "summary": "A de-identified BPS-style case summary request focused on family pressure and uncertainty. This is the strongest end-to-end sample for first-pass validation.",
        "input": (
            "Please organize this de-identified case summary. The client is a 24-year-old recent hire who has had"
            " insomnia for about six months due to family pressure about marriage and anxiety about job performance."
            " After an argument with her father last week, she drank heavily alone but denied self-harm thoughts."
            " She has completed two outside counseling sessions. Current concerns include mood swings, lower"
            " concentration, and avoiding communication with family. Separate known facts, working hypotheses,"
            " and information that still needs verification."
        ),
        "output_style": "supervision_summary",
    },
    {
        "id": "intake_sleep-stress",
        "title": "W1 Demo: Intake guide",
        "workflow": "W1",
        "summary": "A de-identified intake request with sleep issues, family stress, and a mild risk prompt.",
        "input": (
            "Create an intake information guide for a de-identified university student. Over the last two weeks,"
            " graduate-school pressure has worsened her sleep, and conflict with a roommate has increased stress."
            " She has occasionally said she wants to disappear for a while, but she reports no plan and is still"
            " willing to attend classes. Prepare first-session questions and clearly flag the risk and protective"
            " factors that need follow-up."
        ),
        "output_style": "professional_concise",
    },
    {
        "id": "session-sleep-communication",
        "title": "W3 Demo: Session note",
        "workflow": "W3",
        "summary": "A de-identified session note request with clear theme, intervention focus, and risk boundary.",
        "input": (
            "Draft a de-identified session note. The client reports difficulty falling asleep over the last week"
            " and felt hurt after a conversation with her mother. She denies self-harm or suicide plans. This"
            " session focused on emotion labeling and preparing for the next difficult conversation. Generate the"
            " counseling record and preserve any details that still need follow-up."
        ),
        "output_style": "institutional_record",
    },
]

AGENT_STYLE_INSTRUCTIONS = {
    "default": "",
    "professional_concise": (
        "\u8bf7\u4f7f\u7528\u4e13\u4e1a\u3001\u7b80\u6d01\u3001\u6e05\u6670\u7684\u54a8\u8be2\u8bb0\u5f55\u8bed\u8a00\u8f93\u51fa\u3002"
        " Use professional, concise, clear counseling documentation language."
        " Match the user's language unless they ask for a different one."
    ),
    "warm_clinical": (
        "\u8bf7\u4f7f\u7528\u6e29\u548c\u3001\u652f\u6301\u6027\u3001\u4f46\u4ecd\u4fdd\u6301\u4e13\u4e1a\u8fb9\u754c\u7684\u4e34\u5e8a\u8bed\u8a00\u8f93\u51fa\u3002"
        " Use warm, supportive clinical language while maintaining professional boundaries."
        " Match the user's language unless they ask for a different one."
    ),
    "institutional_record": (
        "\u8bf7\u4f7f\u7528\u6b63\u5f0f\u3001\u514b\u5236\u3001\u9002\u5408\u673a\u6784\u7559\u6863\u7684\u8bb0\u5f55\u8bed\u8a00\u8f93\u51fa\u3002"
        " Use formal, restrained language suitable for institutional documentation."
        " Match the user's language unless they ask for a different one."
    ),
    "supervision_summary": (
        "\u8bf7\u4f7f\u7528\u9002\u5408\u7763\u5bfc\u8ba8\u8bba\u7684\u8bed\u8a00\u8f93\u51fa\uff0c\u7a81\u51fa\u4e8b\u5b9e\u3001\u5047\u8bbe\u3001\u98ce\u9669\u8fb9\u754c\u548c\u540e\u7eed\u5de5\u4f5c\u91cd\u70b9\u3002"
        " Write for supervision review, highlighting facts, hypotheses, risk boundaries, and next steps."
        " Match the user's language unless they ask for a different one."
    ),
    "custom": "",
}

WORKFLOW_KEYWORDS = {
    "W1": [
        "intake guide",
        "intake form",
        "intake checklist",
        "initial interview",
        "information gathering",
        "intake",
        "\u521d\u8bbf",
        "\u521d\u59cb\u8bbf\u8c08",
        "\u4fe1\u606f\u6536\u96c6",
        "\u8bbf\u8c08\u8868",
        "\u6536\u96c6\u8868",
        "\u6765\u8bbf\u4fe1\u606f",
    ],
    "W2": [
        "case summary",
        "case formulation",
        "case conceptualization",
        "biopsychosocial",
        "bps",
        "supervision summary",
        "supervision",
        "de-identified case",
        "\u4e2a\u6848\u6982\u5ff5\u5316",
        "\u4e2a\u6848\u4fe1\u606f",
        "\u4e2a\u6848\u80cc\u666f",
        "\u7763\u5bfc",
        "\u53bb\u8bc6\u522b",
    ],
    "W3": [
        "soap",
        "dap",
        "birp",
        "session note",
        "progress note",
        "counseling note",
        "counselling note",
        "risk update",
        "follow-up session",
        "session record",
        "session",
        "note",
        "intervention",
        "next session",
        "\u672c\u6b21\u54a8\u8be2",
        "\u4e0b\u6b21\u54a8\u8be2",
        "\u54a8\u8be2\u8bb0\u5f55",
        "\u98ce\u9669\u53d8\u5316",
        "\u8bb0\u5f55",
        "\u603b\u7ed3",
        "\u5e72\u9884",
        "\u6765\u8bbf\u8005\u53cd\u5e94",
    ],
}


def detect_workflow(user_input):
    text = str(user_input or "").lower()
    if any(keyword in text for keyword in WORKFLOW_KEYWORDS["W1"]):
        return "W1"
    if any(keyword in text for keyword in WORKFLOW_KEYWORDS["W2"]):
        return "W2"
    if any(keyword in text for keyword in WORKFLOW_KEYWORDS["W3"]):
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


def request_is_https(handler):
    if handler is None:
        return False
    proto = str(handler.headers.get("X-Forwarded-Proto", "")).split(",", 1)[0].strip().lower()
    return proto == "https"


def cookie_header(token, max_age=604800, secure=False):
    secure_part = "; Secure" if secure else ""
    return (
        f"{SESSION_COOKIE}={token}; Path=/; Max-Age={max_age}; "
        f"HttpOnly; SameSite=Lax{secure_part}"
    )


def clear_cookie_header(secure=False):
    secure_part = "; Secure" if secure else ""
    return f"{SESSION_COOKIE}=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax{secure_part}"


def cookie_token(handler):
    cookie = SimpleCookie(handler.headers.get("Cookie", ""))
    morsel = cookie.get(SESSION_COOKIE)
    return morsel.value if morsel else ""


def current_user(handler):
    return STORE.session_user(cookie_token(handler))


def env_flag(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def env_int(name, default=None, minimum=None):
    value = os.environ.get(name)
    if value is None or str(value).strip() == "":
        return default
    try:
        parsed = int(str(value).strip())
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer.") from exc
    if minimum is not None and parsed < minimum:
        raise ValueError(f"{name} must be at least {minimum}.")
    return parsed


def auth_config():
    invite_code = str(os.environ.get("WORKBENCH_SIGNUP_INVITE_CODE", "")).strip()
    signup_enabled = env_flag("WORKBENCH_ALLOW_SIGNUP", False) or bool(invite_code)
    return {
        "signup_enabled": signup_enabled,
        "invite_required": bool(invite_code),
    }


def workspace_policy():
    return {
        "max_upload_bytes": env_int("WORKBENCH_MAX_UPLOAD_BYTES", default=10 * 1024 * 1024, minimum=1),
        "retention_days": env_int("WORKBENCH_RETENTION_DAYS", default=None, minimum=1),
        "reset_enabled": True,
    }


def deployment_readiness():
    auth = auth_config()
    policy = workspace_policy()
    username = str(os.environ.get("WORKBENCH_USER", "demo")).strip() or "demo"
    password = str(os.environ.get("WORKBENCH_PASSWORD", "demo123") or "demo123")
    has_deepseek_key = bool(str(os.environ.get("DEEPSEEK_API_KEY", "")).strip())
    default_demo_credentials = username == "demo" and password == "demo123"
    checks = []

    checks.append(
        {
            "id": "deepseek_api",
            "label": "DeepSeek model access",
            "status": "pass" if has_deepseek_key else "fail",
            "detail": (
                "DEEPSEEK_API_KEY is configured for live workflow runs."
                if has_deepseek_key
                else "Missing DEEPSEEK_API_KEY. Live workflow runs will fail on this deployment."
            ),
        }
    )

    auth_status = "pass"
    auth_detail = "Custom workspace credentials are configured for the operator account."
    if not str(os.environ.get("WORKBENCH_USER", "")).strip() or not str(os.environ.get("WORKBENCH_PASSWORD", "")).strip():
        auth_status = "fail"
        auth_detail = "WORKBENCH_USER and WORKBENCH_PASSWORD should both be set for hosted pilot access."
    if default_demo_credentials:
        auth_status = "fail"
        auth_detail = "Deployment is still using the default demo/demo123 login. Replace it before pilot use."
    checks.append(
        {
            "id": "operator_auth",
            "label": "Operator login",
            "status": auth_status,
            "detail": auth_detail,
        }
    )

    signup_status = "warn"
    signup_detail = "Signup is disabled. Operators can still use a shared workspace login."
    if auth["signup_enabled"] and auth["invite_required"]:
        signup_status = "pass"
        signup_detail = "Signup is enabled and protected by an invite code for isolated counselor workspaces."
    elif auth["signup_enabled"]:
        signup_status = "fail"
        signup_detail = "Signup is enabled without WORKBENCH_SIGNUP_INVITE_CODE. Add an invite code before public pilot access."
    checks.append(
        {
            "id": "workspace_signup",
            "label": "Workspace signup",
            "status": signup_status,
            "detail": signup_detail,
        }
    )

    retention_days = policy.get("retention_days")
    checks.append(
        {
            "id": "retention_window",
            "label": "Retention policy",
            "status": "pass" if retention_days else "warn",
            "detail": (
                f"Automatic pruning is enabled after {retention_days} day(s)."
                if retention_days
                else "No retention window is configured. Data pruning is manual only."
            ),
        }
    )

    checks.append(
        {
            "id": "storage_durability",
            "label": "Storage durability",
            "status": "warn",
            "detail": "Workspace data is stored in local service files and SQLite. Export backups frequently because redeploys or instance loss can remove data.",
        }
    )

    fail_count = sum(1 for item in checks if item["status"] == "fail")
    warn_count = sum(1 for item in checks if item["status"] == "warn")
    return {
        "pilot_ready": fail_count == 0,
        "summary": {
            "fail_count": fail_count,
            "warn_count": warn_count,
            "storage_backend": "local_filesystem",
        },
        "checks": checks,
    }


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


def active_upload_root():
    return getattr(STORE, "upload_root", UPLOAD_ROOT)


def user_upload_root(user_id):
    return active_upload_root() / f"user-{int(user_id)}"


def template_ref(kind, value):
    return f"{kind}:{value}"


def upload_template_ref(upload):
    return template_ref("upload", upload["id"])


def serialize_upload(upload):
    payload = dict(upload)
    payload["template_ref"] = upload_template_ref(upload)
    return payload


def demo_template_record(path):
    return {
        "id": path.stem,
        "title": path.stem,
        "template_ref": template_ref("demo", path.stem),
        "summary": "Bundled sample Word template stored in the repository docs directory.",
    }


def require_run_dir_access(user_id, run_dir):
    if not user_id:
        return
    for candidate in [run_dir, *run_dir.parents]:
        record = STORE.get_run_artifact(int(user_id), str(candidate))
        if record:
            return
        if candidate == RUN_ROOT:
            break
    raise PermissionError("Run directory is not available for this account.")


def resolve_demo_template_path(template_id):
    for path in sorted(DOCS_ROOT.glob("*.docx")):
        if path.stem == template_id:
            return path.resolve()
    raise FileNotFoundError("Template file not found.")


def resolve_template_path(path_value=None, user_id=None, allow_run_root=False, template_ref=None):
    if template_ref:
        kind, _, value = str(template_ref).partition(":")
        if not kind or not value:
            raise ValueError("template_ref must use the format kind:value.")
        if kind == "upload":
            if not user_id:
                raise PermissionError("Uploaded templates require an authenticated account.")
            upload = STORE.get_upload(int(user_id), int(value))
            if not upload:
                raise PermissionError("Template is not available for this account.")
            candidate = Path(upload["stored_path"]).resolve()
        elif kind == "demo":
            candidate = resolve_demo_template_path(value)
        else:
            raise ValueError("Unknown template_ref kind.")
    else:
        candidate = Path(str(path_value)).resolve()
    if not candidate.is_file():
        raise FileNotFoundError("Template file not found.")
    if not user_id and not allow_run_root:
        return candidate
    allowed_roots = [DOCS_ROOT.resolve()]
    if user_id:
        allowed_roots.append(user_upload_root(user_id).resolve())
    if allow_run_root:
        allowed_roots.append(RUN_ROOT.resolve())
    if not any(is_relative_to(candidate, root) for root in allowed_roots):
        raise ValueError("Template path must stay inside approved template directories.")
    return candidate


def optional_run_dir(run_dir_value, workflow_id="TEMPLATE", user_id=None):
    if run_dir_value:
        run_dir = Path(str(run_dir_value)).resolve()
        if not run_dir.is_dir():
            raise FileNotFoundError("Run directory not found.")
        if not is_relative_to(run_dir, RUN_ROOT):
            raise PermissionError("Run directory is outside approved output directory.")
        require_run_dir_access(user_id, run_dir)
        return run_dir
    return create_run_dir(run_root=RUN_ROOT, workflow_id=workflow_id)


def apply_output_style(user_input, style="default", custom_style=""):
    style = style if style in AGENT_STYLE_INSTRUCTIONS else "default"
    instruction = custom_style.strip() if style == "custom" else AGENT_STYLE_INSTRUCTIONS[style]
    if not instruction:
        return user_input
    return (
        f"{user_input.strip()}\n\n"
        f"\u8f93\u51fa\u98ce\u683c\u8981\u6c42 / Output style requirement: {instruction}"
    )


def resolve_download_path(path_value, allowed_roots=None):
    allowed_roots = allowed_roots or [RUN_ROOT]
    candidate = Path(str(path_value)).resolve()
    if not candidate.is_file():
        raise FileNotFoundError(str(candidate))
    if not any(is_relative_to(candidate, root) for root in allowed_roots):
        raise ValueError("Download path is outside approved output directories.")
    return candidate


def directory_size(path):
    total = 0
    root = Path(path)
    if not root.exists():
        return 0
    if root.is_file():
        return root.stat().st_size
    for item in root.rglob("*"):
        if item.is_file():
            total += item.stat().st_size
    return total


def safe_content_disposition(filename):
    cleaned = "".join(
        ch if 32 <= ord(ch) < 127 and ch not in {'"', "\\", ";"} else "_"
        for ch in filename
    )
    cleaned = cleaned or "download"
    encoded = quote(filename, safe="")
    return f"attachment; filename=\"{cleaned}\"; filename*=UTF-8''{encoded}"


def authorize_download_path(candidate, user=None):
    upload_root = active_upload_root()
    if is_relative_to(candidate, upload_root):
        if not user:
            raise PermissionError("Download file is not available for this account.")
        if not is_relative_to(candidate, user_upload_root(user["id"])):
            raise PermissionError("Download file is not available for this account.")
        return

    if is_relative_to(candidate, RUN_ROOT):
        if not user:
            return
        require_run_dir_access(user["id"], candidate.parent if candidate.is_file() else candidate)
        return

    raise PermissionError("Download file is not available for this account.")


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


def available_run_files(run_dir):
    files = {}
    for key, filename in RUN_ARTIFACT_FILE_NAMES.items():
        path = run_dir / filename
        if path.exists():
            files[key] = path_for_ui(path)
    return files


def summarize_run_artifact(record):
    run_dir = Path(record["run_dir"]).resolve()
    summary = dict(record)
    summary["run_name"] = run_dir.name
    summary["available_files"] = sorted(path.name for path in run_dir.iterdir() if path.is_file()) if run_dir.is_dir() else []
    summary["download_files"] = available_run_files(run_dir) if run_dir.is_dir() else {}
    return summary


def load_saved_run_payload(run_record):
    run_dir = Path(run_record["run_dir"]).resolve()
    if not run_dir.is_dir():
        raise FileNotFoundError("Run directory not found.")
    result = AgentRunResult(run_record.get("workflow") or "UNKNOWN", "success", run_dir)
    payload = load_run_payload(result)
    payload["available_files"] = available_run_files(run_dir)
    payload["source_action"] = run_record.get("source_action") or ""
    payload["created_at"] = run_record.get("created_at")
    payload["run_name"] = run_dir.name
    return payload


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
            STORE.register_run_artifact(
                user_id,
                path_for_ui(result.run_dir),
                workflow=workflow,
                case_id=resolved_case_id,
                source_action="workflow.run",
            )
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
        require_run_dir_access(payload.get("user_id"), run_dir)
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
        require_run_dir_access(payload.get("user_id"), run_dir)
        template_path = resolve_template_path(
            payload.get("template_path"),
            user_id=payload.get("user_id"),
            template_ref=payload.get("template_ref"),
        )

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
        template_path = resolve_template_path(
            payload.get("template_path"),
            user_id=payload.get("user_id"),
            template_ref=payload.get("template_ref"),
        )
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
        user_id = int(payload["user_id"]) if payload.get("user_id") else None
        raw_input = str(payload.get("raw_input") or "").strip()
        if not raw_input:
            return error_response(400, "Raw input is required.")
        template_path = resolve_template_path(
            payload.get("template_path"),
            user_id=user_id,
            template_ref=payload.get("template_ref"),
        )

        run_dir = optional_run_dir(payload.get("run_dir"), workflow_id="TEMPLATE", user_id=user_id)
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
        if user_id:
            resolved_case_id = int(case_id) if case_id else None
            STORE.register_run_artifact(
                user_id,
                path_for_ui(run_dir),
                workflow="TEMPLATE",
                case_id=resolved_case_id,
                source_action="template.draft",
            )
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


def handle_login(payload, handler=None):
    username = str(payload.get("username") or "").strip()
    password = str(payload.get("password") or "")
    auth = STORE.authenticate(username, password)
    if not auth:
        return error_response(401, "Invalid username or password.")
    STORE.audit(auth["user"]["id"], None, "auth.login", {"username": username})
    append_run_log("auth.login", user_id=auth["user"]["id"], details={"username": username})
    return json_response_with_headers(
        {
            "status": "success",
            "user": auth["user"],
            "expires_at": auth["expires_at"],
            "auth_config": auth_config(),
            "workspace_policy": workspace_policy(),
            "deployment_readiness": deployment_readiness(),
        },
        {"Set-Cookie": cookie_header(auth["token"], secure=request_is_https(handler))},
    )


def handle_signup(payload, handler=None):
    config = auth_config()
    if not config["signup_enabled"]:
        return error_response(403, "Account creation is disabled for this deployment.")

    invite_code = str(os.environ.get("WORKBENCH_SIGNUP_INVITE_CODE", "")).strip()
    provided_invite = str(payload.get("invite_code") or "").strip()
    if invite_code and provided_invite != invite_code:
        return error_response(403, "Invite code is invalid.")

    username = str(payload.get("username") or "").strip()
    password = str(payload.get("password") or "")
    password_confirm = str(payload.get("password_confirm") or "")
    if password != password_confirm:
        return error_response(400, "Password confirmation does not match.")

    try:
        created_user = STORE.create_user(username, password)
    except ValueError as exc:
        return error_response(400, str(exc))

    auth = STORE.authenticate(created_user["username"], password)
    if not auth:
        return error_response(500, "Account created, but sign-in failed.")

    STORE.audit(auth["user"]["id"], None, "auth.signup", {"username": created_user["username"]})
    append_run_log("auth.signup", user_id=auth["user"]["id"], details={"username": created_user["username"]})
    return json_response_with_headers(
        {
            "status": "success",
            "user": auth["user"],
            "expires_at": auth["expires_at"],
            "auth_config": config,
            "workspace_policy": workspace_policy(),
            "deployment_readiness": deployment_readiness(),
        },
        {"Set-Cookie": cookie_header(auth["token"], secure=request_is_https(handler))},
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
        {"Set-Cookie": clear_cookie_header(secure=request_is_https(handler))},
    )


def handle_session(handler):
    user = current_user(handler)
    return json_response(
        {
            "status": "success",
            "user": user,
            "authenticated": bool(user),
            "auth_config": auth_config(),
            "workspace_policy": workspace_policy(),
            "deployment_readiness": deployment_readiness(),
        }
    )


def handle_account(user, payload):
    action = str(payload.get("action") or "").strip().lower()
    if action != "change_password":
        return error_response(400, "Unsupported account action.")

    current_password = str(payload.get("current_password") or "")
    new_password = str(payload.get("new_password") or "")
    new_password_confirm = str(payload.get("new_password_confirm") or "")
    if new_password != new_password_confirm:
        return error_response(400, "New password confirmation does not match.")

    try:
        updated_user = STORE.update_user_password(user["id"], current_password, new_password)
    except ValueError as exc:
        return error_response(400, str(exc))

    STORE.audit(user["id"], None, "auth.password_change", {"username": user["username"]})
    append_run_log("auth.password_change", user_id=user["id"], details={"username": user["username"]})
    return json_response(
        {
            "status": "success",
            "message": "Password updated. Use the new password for future sign-ins.",
            "user": updated_user,
        }
    )


def list_recent_runs(user_id, case_id=None, limit=12):
    if not RUN_LOG_PATH.exists():
        return []

    entries = []
    for line in RUN_LOG_PATH.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if entry.get("user_id") != user_id:
            continue
        if case_id is not None and entry.get("case_id") != case_id:
            continue
        if entry.get("action") not in {"workflow.run", "template.draft", "file.upload", "case.create", "case.update", "case.export"}:
            continue
        entries.append(entry)

    entries.sort(key=lambda item: item.get("timestamp", ""), reverse=True)
    return entries[:limit]


def parse_audit_log_entry(entry):
    parsed = dict(entry)
    details = parsed.get("details")
    if isinstance(details, str):
        try:
            parsed["details"] = json.loads(details)
        except json.JSONDecodeError:
            pass
    return parsed


def case_export_file_name(case_record):
    slug_parts = [f"case-{case_record['id']}"]
    if case_record.get("client_code"):
        slug_parts.append(str(case_record["client_code"]).strip())
    return "-".join(slug_parts) + "-package.zip"


def add_file_to_zip(archive, source_path, archive_path):
    source = Path(source_path)
    if source.is_file():
        archive.write(source, archive_path)
        return True
    return False


def build_case_export_bundle(user, case_record):
    uploads = STORE.list_uploads(user["id"], case_id=case_record["id"])
    audit_logs = [parse_audit_log_entry(item) for item in STORE.list_audit_logs(user["id"], limit=200, case_id=case_record["id"])]
    recent_runs = list_recent_runs(user["id"], case_id=case_record["id"], limit=50)
    run_artifacts = STORE.list_run_artifacts(user["id"], case_id=case_record["id"], limit=50)

    export_dir = create_run_dir(run_root=RUN_ROOT, workflow_id=f"CASE-EXPORT-{case_record['id']}")
    bundle_path = export_dir / case_export_file_name(case_record)
    manifest = {
        "exported_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "case": case_record,
        "artifacts": {
            "upload_count": len(uploads),
            "run_count": len(run_artifacts),
            "audit_log_count": len(audit_logs),
            "recent_activity_count": len(recent_runs),
        },
    }
    included_files = []

    with zipfile.ZipFile(bundle_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("case-summary.json", json.dumps(manifest, ensure_ascii=False, indent=2))
        archive.writestr("audit-log.json", json.dumps(audit_logs, ensure_ascii=False, indent=2))
        archive.writestr("recent-runs.json", json.dumps(recent_runs, ensure_ascii=False, indent=2))

        for upload in uploads:
            source = Path(upload["stored_path"])
            archive_name = f"uploads/{Path(upload['original_name']).name}"
            if add_file_to_zip(archive, source, archive_name):
                included_files.append(archive_name)

        artifact_names = [
            "input.json",
            "prompt_package.txt",
            "metadata.json",
            "raw_output.txt",
            "clean_output.md",
            "structured_output.json",
            "structured_check.json",
            "safety_check.json",
            "output.docx",
            "docx_check.json",
            "filled_template.docx",
            "template_draft.json",
            "template_fill_report.json",
        ]
        for run_record in run_artifacts:
            run_dir = Path(run_record["run_dir"])
            if not is_relative_to(run_dir, RUN_ROOT):
                continue
            for artifact_name in artifact_names:
                source = run_dir / artifact_name
                archive_name = f"runs/{run_dir.name}/{artifact_name}"
                if add_file_to_zip(archive, source, archive_name):
                    included_files.append(archive_name)

    STORE.register_run_artifact(
        user["id"],
        str(export_dir),
        workflow="CASE-EXPORT",
        case_id=case_record["id"],
        source_action="case.export",
    )
    STORE.audit(
        user["id"],
        case_record["id"],
        "case.export",
        {"output_path": path_for_ui(bundle_path), "file_count": len(included_files)},
    )
    append_run_log(
        "case.export",
        user_id=user["id"],
        case_id=case_record["id"],
        details={
            "run_dir": path_for_ui(export_dir),
            "output_path": path_for_ui(bundle_path),
            "file_count": len(included_files),
            "status": "success",
        },
    )
    manifest["artifacts"]["included_files"] = included_files
    return {
        "run_dir": path_for_ui(export_dir),
        "output_path": path_for_ui(bundle_path),
        "manifest": manifest,
    }


def workspace_backup_file_name():
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return f"workspace-backup-{stamp}.zip"


def build_workspace_backup_bundle(user):
    cases = STORE.list_cases(user["id"])
    uploads = STORE.list_uploads(user["id"])
    audit_logs = [parse_audit_log_entry(item) for item in STORE.list_audit_logs(user["id"], limit=1000)]
    recent_activity = list_recent_runs(user["id"], limit=500)
    run_artifacts = STORE.list_run_artifacts(user["id"], limit=500)

    export_dir = create_run_dir(run_root=RUN_ROOT, workflow_id="WORKSPACE-BACKUP")
    bundle_path = export_dir / workspace_backup_file_name()
    workspace_payload = {
        "cases": cases,
        "uploads": [],
        "audit_logs": audit_logs,
        "run_artifacts": [],
        "recent_activity": recent_activity,
    }

    with zipfile.ZipFile(bundle_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for upload in uploads:
            archive_path = f"uploads/{Path(upload['original_name']).name}"
            if add_file_to_zip(archive, upload["stored_path"], archive_path):
                workspace_payload["uploads"].append({**upload, "archive_path": archive_path})

        artifact_names = [
            "input.json",
            "prompt_package.txt",
            "metadata.json",
            "raw_output.txt",
            "clean_output.md",
            "structured_output.json",
            "structured_check.json",
            "safety_check.json",
            "output.docx",
            "docx_check.json",
            "filled_template.docx",
            "template_draft.json",
            "template_fill_report.json",
        ]
        for record in run_artifacts:
            run_dir = Path(record["run_dir"])
            if not run_dir.is_dir() or not is_relative_to(run_dir, RUN_ROOT):
                continue
            files = []
            for artifact_name in artifact_names:
                archive_path = f"runs/{run_dir.name}/{artifact_name}"
                if add_file_to_zip(archive, run_dir / artifact_name, archive_path):
                    files.append(artifact_name)
            workspace_payload["run_artifacts"].append({**record, "run_name": run_dir.name, "files": files})

        manifest = {
            "version": WORKSPACE_BACKUP_VERSION,
            "exported_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "counts": {
                "cases": len(workspace_payload["cases"]),
                "uploads": len(workspace_payload["uploads"]),
                "audit_logs": len(workspace_payload["audit_logs"]),
                "runs": len(workspace_payload["run_artifacts"]),
                "recent_activity": len(workspace_payload["recent_activity"]),
            },
        }
        archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
        archive.writestr("workspace.json", json.dumps(workspace_payload, ensure_ascii=False, indent=2))

    STORE.register_run_artifact(
        user["id"],
        str(export_dir),
        workflow="WORKSPACE-BACKUP",
        source_action="workspace.export",
    )
    STORE.import_audit_log(
        user["id"],
        None,
        "workspace.export",
        {"output_path": path_for_ui(bundle_path), "counts": manifest["counts"]},
    )
    append_run_log(
        "workspace.export",
        user_id=user["id"],
        details={"run_dir": path_for_ui(export_dir), "output_path": path_for_ui(bundle_path), "status": "success"},
    )
    return {"run_dir": path_for_ui(export_dir), "output_path": path_for_ui(bundle_path), "manifest": manifest}


def safe_rmtree(target, approved_root):
    target = Path(target).resolve()
    approved_root = Path(approved_root).resolve()
    if not target.exists():
        return
    if not is_relative_to(target, approved_root):
        raise PermissionError("Refusing to delete outside approved workspace roots.")
    shutil.rmtree(target)


def rewrite_path_values(value, path_map):
    if isinstance(value, dict):
        return {key: rewrite_path_values(item, path_map) for key, item in value.items()}
    if isinstance(value, list):
        return [rewrite_path_values(item, path_map) for item in value]
    if isinstance(value, str):
        return path_map.get(value, value)
    return value


def validated_backup_file_name(name, kind):
    raw_name = str(name or "").strip()
    candidate = Path(raw_name).name
    if not raw_name or candidate != raw_name or candidate in {".", ".."}:
        raise ValueError(f"Unsafe {kind} file name in workspace backup: {raw_name or '<empty>'}.")
    return candidate


def validate_workspace_backup_archive(archive, manifest, workspace):
    if manifest.get("version") != WORKSPACE_BACKUP_VERSION:
        raise ValueError("Unsupported workspace backup version.")

    archive_names = set(archive.namelist())
    expected_names = {"manifest.json", "workspace.json"}
    seen_upload_targets = set()
    seen_run_names = set()

    for upload in workspace.get("uploads", []):
        archive_path = str(upload.get("archive_path") or "").strip()
        if not archive_path:
            raise ValueError("Workspace backup upload is missing archive_path.")
        original_name = validated_backup_file_name(upload.get("original_name"), "upload")
        expected_path = f"uploads/{original_name}"
        if archive_path != expected_path:
            raise ValueError(
                f"Workspace backup upload archive_path mismatch for {original_name}: expected {expected_path}."
            )
        if archive_path in seen_upload_targets:
            raise ValueError(f"Duplicate upload archive_path in workspace backup: {archive_path}.")
        seen_upload_targets.add(archive_path)
        expected_names.add(archive_path)

    for artifact in workspace.get("run_artifacts", []):
        run_name = validated_backup_file_name(artifact.get("run_name"), "run")
        if run_name in seen_run_names:
            raise ValueError(f"Duplicate run_name in workspace backup: {run_name}.")
        seen_run_names.add(run_name)
        for filename in artifact.get("files", []):
            safe_filename = validated_backup_file_name(filename, "run artifact")
            expected_names.add(f"runs/{run_name}/{safe_filename}")

    missing_names = sorted(name for name in expected_names if name not in archive_names)
    if missing_names:
        raise ValueError(f"Workspace backup is missing archive entries: {', '.join(missing_names)}")


def rewrite_run_log_for_user(user_id, replacement_entries=None):
    replacement_entries = replacement_entries or []
    entries = []
    if RUN_LOG_PATH.exists():
        for line in RUN_LOG_PATH.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if entry.get("user_id") == user_id:
                continue
            entries.append(entry)
    entries.extend(replacement_entries)
    entries.sort(key=lambda item: item.get("timestamp", ""))
    RUN_LOG_PATH.write_text(
        "".join(json.dumps(item, ensure_ascii=False) + "\n" for item in entries),
        encoding="utf-8",
    )


def prune_run_log_for_case(user_id, case_id, replacement_entries=None):
    replacement_entries = replacement_entries or []
    entries = []
    if RUN_LOG_PATH.exists():
        for line in RUN_LOG_PATH.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if entry.get("user_id") == user_id and entry.get("case_id") == case_id:
                continue
            entries.append(entry)
    entries.extend(replacement_entries)
    entries.sort(key=lambda item: item.get("timestamp", ""))
    RUN_LOG_PATH.write_text(
        "".join(json.dumps(item, ensure_ascii=False) + "\n" for item in entries),
        encoding="utf-8",
    )


def prune_run_log_before(user_id, before, replacement_entries=None):
    replacement_entries = replacement_entries or []
    cutoff = before if isinstance(before, datetime) else parse_iso(str(before))
    entries = []
    if RUN_LOG_PATH.exists():
        for line in RUN_LOG_PATH.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if entry.get("user_id") == user_id:
                timestamp = entry.get("timestamp")
                if timestamp:
                    try:
                        if parse_iso(timestamp) < cutoff:
                            continue
                    except ValueError:
                        pass
            entries.append(entry)
    entries.extend(replacement_entries)
    entries.sort(key=lambda item: item.get("timestamp", ""))
    RUN_LOG_PATH.write_text(
        "".join(json.dumps(item, ensure_ascii=False) + "\n" for item in entries),
        encoding="utf-8",
    )


def summarize_workspace_status(user):
    summary = STORE.workspace_summary(user["id"])
    recent_activity_count = len(list_recent_runs(user["id"], limit=500))
    upload_bytes = summary.pop("upload_bytes", 0)
    run_bytes = 0
    for record in STORE.list_run_artifacts(user["id"], limit=1000):
        run_dir = Path(record["run_dir"])
        if run_dir.is_dir() and is_relative_to(run_dir, RUN_ROOT):
            run_bytes += directory_size(run_dir)
    summary["counts"]["recent_activity"] = recent_activity_count
    summary["storage"] = {
        "uploads_bytes": upload_bytes,
        "run_artifacts_bytes": run_bytes,
        "total_bytes": upload_bytes + run_bytes,
    }
    return summary


def reset_workspace_data(user):
    cases = STORE.list_cases(user["id"])
    uploads = STORE.list_uploads(user["id"])
    run_artifacts = STORE.list_run_artifacts(user["id"], limit=1000)
    audit_logs = STORE.list_audit_logs(user["id"], limit=1000)
    recent_activity_count = len(list_recent_runs(user["id"], limit=500))

    for record in run_artifacts:
        run_dir = Path(record["run_dir"])
        if run_dir.exists():
            safe_rmtree(run_dir, RUN_ROOT)
    upload_root = user_upload_root(user["id"])
    if upload_root.exists():
        safe_rmtree(upload_root, active_upload_root())
    STORE.clear_workspace(user["id"])
    rewrite_run_log_for_user(user["id"])
    STORE.import_audit_log(
        user["id"],
        None,
        "workspace.reset",
        {
            "counts": {
                "cases": len(cases),
                "uploads": len(uploads),
                "run_artifacts": len(run_artifacts),
                "audit_logs": len(audit_logs),
                "recent_activity": recent_activity_count,
            }
        },
    )
    append_run_log("workspace.reset", user_id=user["id"], details={"status": "success"})
    return {
        "counts": {
            "cases": len(cases),
            "uploads": len(uploads),
            "run_artifacts": len(run_artifacts),
            "audit_logs": len(audit_logs),
            "recent_activity": recent_activity_count,
        }
    }


def prune_workspace_retention(user):
    policy = workspace_policy()
    retention_days = policy.get("retention_days")
    if not retention_days:
        raise ValueError("WORKBENCH_RETENTION_DAYS is not configured for this deployment.")
    cutoff = utc_now() - timedelta(days=retention_days)
    pruned = STORE.prune_workspace_data(user["id"], cutoff)
    prune_run_log_before(user["id"], cutoff)
    STORE.import_audit_log(
        user["id"],
        None,
        "workspace.prune",
        {
            "cutoff": pruned["cutoff"],
            "retention_days": retention_days,
            "counts": pruned["counts"],
            "bytes_removed": pruned["bytes_removed"],
        },
    )
    append_run_log(
        "workspace.prune",
        user_id=user["id"],
        details={
            "status": "success",
            "cutoff": pruned["cutoff"],
            "retention_days": retention_days,
            "counts": pruned["counts"],
        },
    )
    return {
        "policy": policy,
        "summary": summarize_workspace_status(user),
        "pruned": pruned,
    }


def restore_workspace_backup_bundle(user, backup_path):
    with zipfile.ZipFile(backup_path) as archive:
        try:
            manifest = json.loads(archive.read("manifest.json").decode("utf-8"))
            workspace = json.loads(archive.read("workspace.json").decode("utf-8"))
        except KeyError as exc:
            raise ValueError(f"Backup bundle is missing {exc.args[0]}.")
        validate_workspace_backup_archive(archive, manifest, workspace)

        for record in STORE.list_run_artifacts(user["id"], limit=1000):
            run_dir = Path(record["run_dir"])
            if run_dir.exists():
                safe_rmtree(run_dir, RUN_ROOT)
        upload_root = user_upload_root(user["id"])
        if upload_root.exists():
            safe_rmtree(upload_root, active_upload_root())
        STORE.clear_workspace(user["id"])
        rewrite_run_log_for_user(user["id"])

        case_id_map = {}
        path_map = {}
        for case_record in workspace.get("cases", []):
            imported = STORE.import_case(
                user["id"],
                str(case_record.get("title") or "Untitled case"),
                client_code=str(case_record.get("client_code") or ""),
                notes=str(case_record.get("notes") or ""),
                created_at=case_record.get("created_at"),
                updated_at=case_record.get("updated_at"),
            )
            case_id_map[case_record.get("id")] = imported["id"]

        for upload in workspace.get("uploads", []):
            archive_path = upload.get("archive_path")
            if not archive_path:
                continue
            original_name = validated_backup_file_name(upload.get("original_name"), "upload")
            case_id = case_id_map.get(upload.get("case_id"))
            case_part = f"case-{case_id}" if case_id else "unassigned"
            target_dir = user_upload_root(user["id"]) / case_part
            target_dir.mkdir(parents=True, exist_ok=True)
            target_path = target_dir / original_name
            target_path.write_bytes(archive.read(archive_path))
            imported_upload = STORE.import_upload_record(
                user["id"],
                case_id,
                original_name,
                str(target_path),
                content_type=str(upload.get("content_type") or ""),
                size_bytes=upload.get("size_bytes") or target_path.stat().st_size,
                created_at=upload.get("created_at"),
            )
            path_map[upload.get("stored_path")] = imported_upload["stored_path"]

        for artifact in workspace.get("run_artifacts", []):
            run_name = validated_backup_file_name(artifact.get("run_name"), "run")
            run_dir = create_run_dir(run_root=RUN_ROOT, workflow_id=f"RESTORE-{run_name}")
            for filename in artifact.get("files", []):
                safe_filename = validated_backup_file_name(filename, "run artifact")
                source_name = f"runs/{run_name}/{safe_filename}"
                target_path = run_dir / safe_filename
                target_path.parent.mkdir(parents=True, exist_ok=True)
                target_path.write_bytes(archive.read(source_name))
            STORE.register_run_artifact(
                user["id"],
                str(run_dir),
                workflow=str(artifact.get("workflow") or ""),
                case_id=case_id_map.get(artifact.get("case_id")),
                source_action=str(artifact.get("source_action") or ""),
                created_at=artifact.get("created_at"),
            )
            path_map[artifact.get("run_dir")] = str(run_dir.resolve())

        for log in workspace.get("audit_logs", []):
            STORE.import_audit_log(
                user["id"],
                case_id_map.get(log.get("case_id")),
                str(log.get("action") or "workspace.restore"),
                rewrite_path_values(log.get("details") or {}, path_map),
                created_at=log.get("created_at"),
            )

        restored_activity = []
        for entry in workspace.get("recent_activity", []):
            restored_activity.append(
                {
                    "timestamp": entry.get("timestamp") or datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    "action": str(entry.get("action") or "workspace.restore"),
                    "user_id": user["id"],
                    "case_id": case_id_map.get(entry.get("case_id")),
                    "details": rewrite_path_values(entry.get("details") or {}, path_map),
                }
            )
        rewrite_run_log_for_user(user["id"], replacement_entries=restored_activity)

    STORE.import_audit_log(user["id"], None, "workspace.restore", {"counts": manifest.get("counts", {})})
    append_run_log("workspace.restore", user_id=user["id"], details={"status": "success"})
    return {"manifest": manifest, "counts": manifest.get("counts", {})}


def handle_workspace(user, payload=None):
    payload = payload or {}
    action = payload.get("action") or "status"
    if action == "status":
        return json_response(
            {
                "status": "success",
                "policy": workspace_policy(),
                "summary": summarize_workspace_status(user),
            }
        )
    if action == "export":
        return json_response({"status": "success", **build_workspace_backup_bundle(user)})
    if action == "restore":
        backup_b64 = str(payload.get("backup_base64") or "").strip()
        if not backup_b64:
            return error_response(400, "backup_base64 is required.")
        try:
            backup_bytes = base64.b64decode(backup_b64)
        except Exception:
            return error_response(400, "backup_base64 is not valid base64.")
        with tempfile.TemporaryDirectory() as tmp:
            backup_path = Path(tmp) / "workspace-backup.zip"
            backup_path.write_bytes(backup_bytes)
            try:
                result = restore_workspace_backup_bundle(user, backup_path)
            except (ValueError, PermissionError, FileNotFoundError, zipfile.BadZipFile) as exc:
                return error_response(400, str(exc))
        return json_response({"status": "success", **result})
    if action == "prune":
        try:
            result = prune_workspace_retention(user)
        except ValueError as exc:
            return error_response(400, str(exc))
        return json_response({"status": "success", **result})
    if action == "reset":
        confirm_text = str(payload.get("confirm_text") or "").strip()
        if confirm_text != "DELETE WORKSPACE":
            return error_response(400, 'confirm_text must be "DELETE WORKSPACE".')
        return json_response(
            {
                "status": "success",
                "summary": reset_workspace_data(user),
                "policy": workspace_policy(),
            }
        )
    return error_response(400, "Unknown workspace action.")


def handle_runs(user, payload=None):
    payload = payload or {}
    action = payload.get("action") or "list"
    if action == "detail":
        run_dir = str(payload.get("run_dir") or "").strip()
        if not run_dir:
            return error_response(400, "run_dir is required.")
        run_record = STORE.get_run_artifact(user["id"], run_dir)
        if not run_record:
            return error_response(404, "Run not found.")
        try:
            require_run_dir_access(user["id"], Path(run_record["run_dir"]))
            return json_response({"status": "success", **load_saved_run_payload(run_record)})
        except (FileNotFoundError, PermissionError, ValueError) as exc:
            return error_response(400, str(exc))
    case_id = payload.get("case_id")
    run_artifacts = STORE.list_run_artifacts(user["id"], case_id=int(case_id) if case_id else None)
    return json_response(
        {
            "status": "success",
            "runs": [summarize_run_artifact(record) for record in run_artifacts],
        }
    )


def handle_cases(user, payload=None):
    payload = payload or {}
    if payload.get("action") == "demo_catalog":
        return handle_demo_catalog()
    if payload.get("action") == "create":
        case_record = STORE.create_case(
            user["id"],
            str(payload.get("title") or "Untitled case"),
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
    if payload.get("action") == "detail":
        case_id = int(payload.get("case_id") or 0)
        case_record = STORE.get_case(user["id"], case_id)
        if not case_record:
            return error_response(404, "Case not found.")
        run_artifacts = STORE.list_run_artifacts(user["id"], case_id=case_id)
        return json_response(
            {
                "status": "success",
                "case": case_record,
                "uploads": [serialize_upload(item) for item in STORE.list_uploads(user["id"], case_id=case_id)],
                "audit_logs": STORE.list_audit_logs(user["id"], case_id=case_id),
                "recent_runs": list_recent_runs(user["id"], case_id=case_id),
                "run_artifacts": [summarize_run_artifact(record) for record in run_artifacts],
            }
        )
    if payload.get("action") == "export":
        case_id = int(payload.get("case_id") or 0)
        case_record = STORE.get_case(user["id"], case_id)
        if not case_record:
            return error_response(404, "Case not found.")
        export_payload = build_case_export_bundle(user, case_record)
        return json_response({"status": "success", **export_payload})
    if payload.get("action") == "delete":
        case_id = int(payload.get("case_id") or 0)
        deleted = STORE.delete_case(user["id"], case_id)
        if not deleted:
            return error_response(404, "Case not found.")
        deletion_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "action": "case.delete",
            "user_id": user["id"],
            "case_id": None,
            "details": {
                "deleted_case_id": case_id,
                "title": deleted["case"]["title"],
                "client_code": deleted["case"]["client_code"],
                "counts": deleted["counts"],
            },
        }
        prune_run_log_for_case(user["id"], case_id, replacement_entries=[deletion_entry])
        STORE.import_audit_log(
            user["id"],
            None,
            "case.delete",
            {
                "deleted_case_id": case_id,
                "title": deleted["case"]["title"],
                "client_code": deleted["case"]["client_code"],
                "counts": deleted["counts"],
            },
        )
        return json_response(
            {
                "status": "success",
                "deleted_case": deleted["case"],
                "summary": deleted,
                "cases": STORE.list_cases(user["id"]),
            }
        )
    return json_response({"status": "success", "cases": STORE.list_cases(user["id"])})


def handle_upload(user, payload):
    filename = str(payload.get("filename") or "").strip()
    content_b64 = str(payload.get("content_base64") or "")
    if not filename or not content_b64:
        return error_response(400, "filename and content_base64 are required.")
    policy = workspace_policy()
    max_upload_bytes = policy["max_upload_bytes"]
    try:
        upload_bytes = len(base64.b64decode(content_b64))
    except Exception:
        return error_response(400, "content_base64 is not valid base64.")
    if upload_bytes > max_upload_bytes:
        return error_response(400, f"Upload exceeds the deployment limit of {max_upload_bytes} bytes.")
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
    return json_response({"status": "success", "upload": serialize_upload(upload), "policy": policy})


def handle_uploads(user, payload=None):
    payload = payload or {}
    case_id = payload.get("case_id")
    return json_response(
        {
            "status": "success",
            "uploads": [serialize_upload(item) for item in STORE.list_uploads(user["id"], case_id=int(case_id) if case_id else None)],
        }
    )


def handle_audit_logs(user):
    return json_response({"status": "success", "audit_logs": STORE.list_audit_logs(user["id"])})


def list_demo_templates():
    return [demo_template_record(path) for path in sorted(DOCS_ROOT.glob("*.docx"))]


def handle_demo_catalog():
    return json_response(
        {
            "status": "success",
            "scenarios": DEMO_SCENARIOS,
            "templates": list_demo_templates(),
            "privacy_notice": "Use de-identified demo material only. Avoid names, phone numbers, IDs, and real client data in public MVP validation.",
        }
    )


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


def handle_file_download(request_path, user=None):
    parsed = urlparse(request_path)
    if not parsed.path.startswith("/files/"):
        return error_response(404, "File endpoint not found.")
    encoded_path = parsed.path[len("/files/") :]
    allowed_roots = [RUN_ROOT, active_upload_root()]
    try:
        target = resolve_download_path(unquote(encoded_path), allowed_roots=allowed_roots)
        authorize_download_path(target, user=user)
    except PermissionError as exc:
        return error_response(403, str(exc))
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
        if path in {"/api/demo-catalog", "/api/demo_catalog"}:
            user, error = require_user(self)
            if error:
                send_response_tuple(self, error)
                return
            send_response_tuple(self, handle_demo_catalog())
            return

        if self.path.startswith("/files/"):
            user, error = require_user(self)
            if error:
                send_response_tuple(self, error)
                return
            try:
                response = handle_file_download(self.path, user=user)
            except FileNotFoundError:
                response = error_response(404, "Download file not found.")
            except PermissionError as exc:
                response = error_response(403, str(exc))
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
            response = handle_login(payload, handler=self)
            send_response_tuple(self, response)
            return
        if path == "/api/signup":
            response = handle_signup(payload, handler=self)
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
        elif path == "/api/runs":
            response = handle_runs(user, payload)
        elif path == "/api/upload":
            response = handle_upload(user, payload)
        elif path == "/api/audit":
            response = handle_audit_logs(user)
        elif path in {"/api/demo-catalog", "/api/demo_catalog"}:
            response = handle_demo_catalog()
        elif path == "/api/account":
            response = handle_account(user, payload)
        elif path == "/api/workspace":
            response = handle_workspace(user, payload)
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
