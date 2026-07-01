import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Callable


DEFAULT_WORKFLOW = "W2"
DEFAULT_INPUT = (
    "Please organize this de-identified case summary. The client is a 24-year-old recent hire who has had "
    "insomnia for about six months due to family pressure about marriage and anxiety about job performance. "
    "After an argument with her father last week, she drank heavily alone but denied self-harm thoughts. "
    "Separate known facts, working hypotheses, risk boundaries, and information that still needs verification."
)


def _normalize_base_url(base_url):
    return str(base_url or "").rstrip("/")


def request_json(base_url, path, method="GET", payload=None, headers=None, timeout=30):
    url = f"{_normalize_base_url(base_url)}{path}"
    encoded = None
    merged_headers = {"Accept": "application/json"}
    if headers:
        merged_headers.update(headers)
    if payload is not None:
        encoded = json.dumps(payload).encode("utf-8")
        merged_headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=encoded, method=method.upper(), headers=merged_headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read()
            text = body.decode("utf-8") if body else "{}"
            data = json.loads(text)
            return response.status, data, dict(response.headers.items())
    except urllib.error.HTTPError as exc:
        body = exc.read()
        text = body.decode("utf-8") if body else "{}"
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            data = {"status": "error", "message": text or f"HTTP {exc.code}"}
        return exc.code, data, dict(exc.headers.items())


def _cookie_header(response_headers):
    for key, value in response_headers.items():
        if str(key).lower() == "set-cookie" and value:
            return value.split(";", 1)[0]
    return ""


def _validate_readiness(readiness, expect_pilot_ready):
    if not isinstance(readiness, dict):
        raise ValueError("Deployment readiness payload is missing.")
    if expect_pilot_ready and not readiness.get("pilot_ready"):
        summary = readiness.get("summary") or {}
        raise ValueError(
            f"Deployment readiness check failed: pilot_ready=false "
            f"(fail_count={summary.get('fail_count', 'unknown')}, warn_count={summary.get('warn_count', 'unknown')})."
        )


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _run_step(report, name, fn):
    result = fn()
    report["checks"].append(name)
    return result


def run_smoke(
    base_url,
    username="",
    password="",
    invite_code="",
    workflow=DEFAULT_WORKFLOW,
    input_text=DEFAULT_INPUT,
    timeout=30,
    expect_pilot_ready=False,
    expect_detected_workflow="",
    expect_route_status="",
    expect_route_notice_substring="",
    expect_w1_mode="",
    expect_route_summary_substring="",
    expect_w1_summary_brief=False,
    require_signup=False,
    skip_auth=False,
    skip_run=False,
    real_run=False,
    request_json: Callable = request_json,
):
    report = {
        "base_url": _normalize_base_url(base_url),
        "checks": [],
        "auth_mode": None,
        "deployment_readiness": None,
        "workflow": None,
    }

    def health_step():
        status, payload, _headers = request_json(report["base_url"], "/health", timeout=timeout)
        _require(status == 200, f"/health returned HTTP {status}.")
        _require(payload.get("status") == "ok", "/health did not return status=ok.")
        return payload

    _run_step(report, "health", health_step)

    def service_info_step():
        status, payload, _headers = request_json(report["base_url"], "/service-info", timeout=timeout)
        _require(status == 200, f"/service-info returned HTTP {status}.")
        _require(payload.get("openapi", "").endswith("/openapi.json"), "/service-info is missing the OpenAPI URL.")
        readiness = payload.get("deployment_readiness")
        _validate_readiness(readiness, expect_pilot_ready)
        report["deployment_readiness"] = readiness
        return payload

    _run_step(report, "service_info", service_info_step)

    def openapi_step():
        status, payload, _headers = request_json(report["base_url"], "/openapi.json", timeout=timeout)
        _require(status == 200, f"/openapi.json returned HTTP {status}.")
        paths = payload.get("paths") or {}
        _require("/run_workflow" in paths, "OpenAPI spec is missing /run_workflow.")
        _require("/draft_template" in paths, "OpenAPI spec is missing /draft_template.")
        return payload

    _run_step(report, "openapi", openapi_step)

    auth_headers = {}
    auth_config = {}

    if not skip_auth:
        def session_step():
            status, payload, _headers = request_json(report["base_url"], "/api/session", timeout=timeout)
            _require(status == 200, f"/api/session returned HTTP {status}.")
            readiness = payload.get("deployment_readiness")
            if readiness:
                _validate_readiness(readiness, expect_pilot_ready)
                report["deployment_readiness"] = readiness
            return payload

        session_payload = _run_step(report, "session", session_step)
        auth_config = session_payload.get("auth_config") or {}
        auth_mode = "signup" if require_signup else "login"
        if require_signup:
            _require(auth_config.get("signup_enabled"), "Signup was required, but this deployment has signup disabled.")
            _require(invite_code or not auth_config.get("invite_required"), "Signup requires an invite code.")
        _require(username and password, "username and password are required when authentication is enabled.")

        def auth_step():
            path = "/api/signup" if auth_mode == "signup" else "/api/login"
            payload = {"username": username, "password": password}
            if auth_mode == "signup":
                payload["password_confirm"] = password
                if invite_code:
                    payload["invite_code"] = invite_code
            status, auth_payload, response_headers = request_json(
                report["base_url"],
                path,
                method="POST",
                payload=payload,
                timeout=timeout,
            )
            _require(status == 200, f"{path} returned HTTP {status}: {auth_payload.get('message', 'request failed')}")
            _require(auth_payload.get("status") == "success", f"{path} did not return success.")
            cookie = _cookie_header(response_headers)
            _require(cookie, f"{path} did not return a session cookie.")
            auth_headers["Cookie"] = cookie
            report["auth_mode"] = auth_mode
            return auth_payload

        _run_step(report, "auth", auth_step)

    if not skip_run:
        def run_step():
            status, payload, _headers = request_json(
                report["base_url"],
                "/api/run",
                method="POST",
                payload={
                    "workflow": workflow,
                    "input": input_text,
                    "structured": True,
                    "render_docx": False,
                    "output_style": "professional_concise",
                },
                headers=auth_headers,
                timeout=timeout,
            )
            _require(status == 200, f"/api/run returned HTTP {status}: {payload.get('message', 'request failed')}")
            _require(payload.get("status") == "success", "/api/run did not return success.")
            excerpt = (payload.get("clean_output") or payload.get("raw_output") or "").strip()
            _require(
                excerpt or payload.get("structured_output"),
                "/api/run returned neither readable output nor structured_output.",
            )
            report["workflow"] = {
                "workflow": payload.get("workflow") or workflow,
                "detected_workflow": payload.get("detected_workflow") or "",
                "route_status": payload.get("route_status") or "",
                "route_notice": payload.get("route_notice") or "",
                "w1_mode": payload.get("w1_mode") or "",
                "routing_reasons_summary": payload.get("routing_reasons_summary") or "",
                "output_excerpt": excerpt[:240],
                "real_run": bool(real_run),
            }
            if expect_detected_workflow:
                _require(
                    payload.get("detected_workflow") == expect_detected_workflow,
                    f"/api/run detected_workflow={payload.get('detected_workflow')!r}, expected {expect_detected_workflow!r}.",
                )
            if expect_route_status:
                _require(
                    payload.get("route_status") == expect_route_status,
                    f"/api/run route_status={payload.get('route_status')!r}, expected {expect_route_status!r}.",
                )
            if expect_route_notice_substring:
                route_notice = payload.get("route_notice") or ""
                _require(
                    expect_route_notice_substring in route_notice,
                    f"/api/run route_notice did not include {expect_route_notice_substring!r}.",
                )
            if expect_w1_mode:
                _require(
                    payload.get("w1_mode") == expect_w1_mode,
                    f"/api/run w1_mode={payload.get('w1_mode')!r}, expected {expect_w1_mode!r}.",
                )
            if expect_route_summary_substring:
                routing_summary = payload.get("routing_reasons_summary") or ""
                _require(
                    expect_route_summary_substring in routing_summary,
                    f"/api/run routing_reasons_summary did not include {expect_route_summary_substring!r}.",
                )
            if expect_w1_summary_brief:
                _require(
                    isinstance(payload.get("w1_summary_brief"), dict) and bool(payload.get("w1_summary_brief")),
                    "/api/run did not return a populated w1_summary_brief payload.",
                )
            return payload

        _run_step(report, "workflow_run", run_step)

    return report


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Smoke test the hosted counselor assistant web product.")
    parser.add_argument("--base-url", required=True, help="Hosted base URL, for example https://your-service.onrender.com")
    parser.add_argument("--username", default="", help="Operator username or the new signup username.")
    parser.add_argument("--password", default="", help="Operator password or the new signup password.")
    parser.add_argument("--invite-code", default="", help="Signup invite code when signup is enabled.")
    parser.add_argument("--workflow", default=DEFAULT_WORKFLOW, choices=["AUTO", "W1", "W2", "W3", "W4", "W5", "W6"])
    parser.add_argument("--input", default=DEFAULT_INPUT, help="Workflow input text used for smoke validation.")
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--expect-pilot-ready", action="store_true")
    parser.add_argument("--expect-detected-workflow", default="", help="Expected detected_workflow in /api/run.")
    parser.add_argument("--expect-route-status", default="", help="Expected route_status in /api/run, for example mixed_signals.")
    parser.add_argument("--expect-route-notice-substring", default="", help="Substring that must appear in route_notice.")
    parser.add_argument("--expect-w1-mode", default="", help="Expected W1 mode in /api/run, for example initial_interview_summary.")
    parser.add_argument("--expect-route-summary-substring", default="", help="Substring that must appear in routing_reasons_summary.")
    parser.add_argument("--expect-w1-summary-brief", action="store_true", help="Require a populated w1_summary_brief payload.")
    parser.add_argument("--require-signup", action="store_true")
    parser.add_argument("--skip-auth", action="store_true")
    parser.add_argument("--skip-run", action="store_true")
    parser.add_argument("--real-run", action="store_true", help="Annotate the report as a live model run.")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    report = run_smoke(
        args.base_url,
        username=args.username,
        password=args.password,
        invite_code=args.invite_code,
        workflow=args.workflow,
        input_text=args.input,
        timeout=args.timeout,
        expect_pilot_ready=args.expect_pilot_ready,
        expect_detected_workflow=args.expect_detected_workflow,
        expect_route_status=args.expect_route_status,
        expect_route_notice_substring=args.expect_route_notice_substring,
        expect_w1_mode=args.expect_w1_mode,
        expect_route_summary_substring=args.expect_route_summary_substring,
        expect_w1_summary_brief=args.expect_w1_summary_brief,
        require_signup=args.require_signup,
        skip_auth=args.skip_auth,
        skip_run=args.skip_run,
        real_run=args.real_run,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValueError as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
        raise SystemExit(1)
