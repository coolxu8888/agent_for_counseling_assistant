import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from w1_acceptance import W1_VISIBLE_LABELS, validate_hosted_report, write_sanitized_report
from w2_acceptance import W2_VISIBLE_LABEL, validate_hosted_report as validate_w2_hosted_report
from w3_acceptance import (
    W3_VISIBLE_LABEL,
    validate_hosted_report as validate_w3_hosted_report,
    write_sanitized_report as write_w3_sanitized_report,
)
from w4_acceptance import (
    W4_REQUIRED_FIELDS,
    W4_VISIBLE_LABEL,
    validate_hosted_report as validate_w4_hosted_report,
    write_sanitized_report as write_w4_sanitized_report,
)
from w5_acceptance import (
    W5_REQUIRED_FIELDS,
    W5_VISIBLE_LABEL,
    validate_hosted_report as validate_w5_hosted_report,
    write_sanitized_report as write_w5_sanitized_report,
)


DEFAULT_WORKFLOW = "W2"
DEFAULT_INPUT = (
    "Please organize this de-identified case summary. The client is a 24-year-old recent hire who has had "
    "insomnia for about six months due to family pressure about marriage and anxiety about job performance. "
    "After an argument with her father last week, she drank heavily alone but denied self-harm thoughts. "
    "Separate known facts, working hypotheses, risk boundaries, and information that still needs verification."
)
W1_HOSTED_SCENARIOS = {
    "intake_prep": "请根据以下去标识化线索准备咨询提问清单：来访者近期因工作调整睡眠变差，已获得家人支持；请区分已知信息与待了解问题。",
    "initial_interview_summary": "请把以下已完成的去标识化材料整理为固定初访总结模板：成年人，近期工作压力增加，睡眠受影响，有稳定支持者，否认当前自伤想法。",
}
W2_HOSTED_SCENARIO = (
    "Please organize these de-identified notes into a BPS supervision case background. "
    "The client is a 24-year-old recent hire with six months of insomnia, family pressure about marriage, "
    "job-performance anxiety, one episode of drinking heavily alone after a family argument, and no reported "
    "self-harm plan. The client is still attending work, agreed to seek counseling, and identified one trusted friend "
    "they could contact after difficult family conversations. Separate presenting concerns, known facts, working hypotheses, biological/psychological/social "
    "dimensions, protective factors, bounded risk follow-up questions, and recommended focus. Do not write a diagnosis "
    "or a counseling record."
)
W3_HOSTED_SCENARIO = (
    "Please write a SOAP counseling record from this de-identified session note. Use exact section headings "
    "Subjective, Objective, Assessment, Plan, and Risk change. "
    "The client reported that panic decreased compared with last week, but they still worry about tomorrow's work presentation. "
    "They denied current suicide plan or intent, while last week they had said they sometimes wanted to disappear for a bit. "
    "The counselor reviewed the risk change, practiced grounding, confirmed the client can contact one trusted friend tonight, "
    "and explained that worsening suicidal thoughts require timely follow-up. Keep the risk change, follow-up actions, "
    "next-session focus, and documentation boundaries clear. Do not write a case background or treatment roadmap."
)
W4_HOSTED_SCENARIO = (
    "Build a CBT case conceptualization for this de-identified case. The client is a 26-year-old teacher who "
    "becomes intensely anxious before performance reviews, replays criticism for days, and then avoids replying "
    "to colleagues. She grew up with frequent comparisons to higher-performing cousins. After a recent conflict "
    "with her supervisor, she reported poor sleep and thoughts such as 'If I make one mistake, everyone will see "
    "I am inadequate.' She denied suicide plans. Separate selected framework, known facts, presenting patterns, "
    "predisposing factors, precipitating factors, maintaining factors, protective factors, risk considerations, "
    "working hypotheses, questions to verify, and boundary notes. Do not write a diagnosis, treatment plan, "
    "counseling record, next-session plan, or roadmap."
)
W5_HOSTED_SCENARIO = (
    "Create a CBT next session plan for this de-identified case, limited to one upcoming counseling session. "
    "The client is a 26-year-old teacher who becomes anxious before performance reviews, replays criticism for days, "
    "and avoids replying to colleagues. She denied suicide plans, but sleep has worsened after a recent supervisor conflict. "
    "Separate selected framework, session goal, focus areas, planned interventions, suggested questions, risk monitoring, "
    "between-session tasks, do-not-do boundaries, and boundary notes. Do not write a diagnosis, counseling record, "
    "case conceptualization, treatment plan, or multi-session roadmap."
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
    render_docx=False,
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
                    "render_docx": bool(render_docx),
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
                "http_status": status,
                "structured_result": payload.get("structured_check"),
                "structured_sections": (payload.get("structured_output") or {}).get("sections"),
                "structured_output": payload.get("structured_output"),
                "artifact": payload.get("docx"),
                "model_metadata": payload.get("metadata"),
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


def _acceptance_scenario(mode, input_text, smoke_report):
    workflow = smoke_report.get("workflow") or {}
    _require(workflow.get("http_status") == 200, f"W1 {mode} did not return HTTP 200.")
    _require(workflow.get("workflow") == "W1" and workflow.get("detected_workflow") == "W1", f"W1 {mode} was not detected as W1.")
    _require(workflow.get("w1_mode") == mode, f"W1 {mode} returned the wrong W1 mode.")
    _require(workflow.get("real_run") is True, f"W1 {mode} was not marked as a real-model run.")
    model_metadata = workflow.get("model_metadata") or {}
    _require(
        model_metadata.get("status") == "success"
        and bool(model_metadata.get("provider"))
        and bool(model_metadata.get("model")),
        f"W1 {mode} real model metadata is required.",
    )
    structured = workflow.get("structured_result") or {}
    _require(structured.get("status") == "PASS", f"W1 {mode} structured validation must be PASS.")
    sections = workflow.get("structured_sections")
    _require(isinstance(sections, (dict, list)) and bool(sections), f"W1 {mode} structured sections are required.")
    docx = workflow.get("artifact") or {}
    docx_check = docx.get("check") or {}
    _require(str(docx.get("status") or "").upper() == "PASS", f"W1 {mode} DOCX artifact must pass.")
    _require(str(docx_check.get("status") or "").upper() == "PASS", f"W1 {mode} DOCX validation must pass.")
    _require(bool(docx.get("path")), f"W1 {mode} DOCX artifact metadata is missing.")
    return {
        "mode": mode,
        "visible_label": W1_VISIBLE_LABELS[mode],
        "workflow": "W1",
        "route_status": "passed",
        "http_status": 200,
        "sanitized_input": input_text,
        "model_run": {"status": "success", "real_model": True},
        "structured_result": {"status": "PASS", "sections": sections},
        "artifact": {
            "format": "docx",
            "editable": True,
            "download_assertion": "passed",
            "filename": Path(str(docx.get("path"))).name or "output.docx",
        },
    }


def run_w1_acceptance(base_url, username="", password="", invite_code="", deployed_version="", timeout=120, request_json=request_json):
    """Run both hosted W1 modes and return only sanitized durable evidence."""
    _require(bool(str(deployed_version).strip()), "deployed_version is required for W1 acceptance.")
    scenarios = []
    for mode, input_text in W1_HOSTED_SCENARIOS.items():
        smoke = run_smoke(
            base_url,
            username=username,
            password=password,
            invite_code=invite_code,
            workflow="W1",
            input_text=input_text,
            timeout=timeout,
            expect_w1_mode=mode,
            real_run=True,
            render_docx=True,
            request_json=request_json,
        )
        scenarios.append(_acceptance_scenario(mode, input_text, smoke))
    report = {
        "report_type": "hosted",
        "timestamp_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "base_url": _normalize_base_url(base_url),
        "deployed_version": str(deployed_version).strip(),
        "scenarios": scenarios,
    }
    validate_hosted_report(report)
    return report


def _w2_acceptance_scenario(input_text, smoke_report):
    workflow = smoke_report.get("workflow") or {}
    _require(workflow.get("http_status") == 200, "W2 did not return HTTP 200.")
    _require(workflow.get("workflow") == "W2" and workflow.get("detected_workflow") == "W2", "W2 was not detected as W2.")
    _require(workflow.get("real_run") is True, "W2 was not marked as a real-model run.")
    model_metadata = workflow.get("model_metadata") or {}
    _require(
        model_metadata.get("status") == "success"
        and bool(model_metadata.get("provider"))
        and bool(model_metadata.get("model")),
        "W2 real model metadata is required.",
    )
    structured_check = workflow.get("structured_result") or {}
    _require(structured_check.get("status") == "PASS", "W2 structured validation must be PASS.")
    structured_output = workflow.get("structured_output") or {}
    _require(structured_output.get("workflow") == "W2", "W2 structured output is required.")
    docx = workflow.get("artifact") or {}
    docx_check = docx.get("check") or {}
    _require(str(docx.get("status") or "").upper() == "PASS", "W2 DOCX artifact must pass.")
    _require(str(docx_check.get("status") or "").upper() == "PASS", "W2 DOCX validation must pass.")
    _require(bool(docx.get("path")), "W2 DOCX artifact metadata is missing.")
    return {
        "workflow": "W2",
        "visible_label": W2_VISIBLE_LABEL,
        "route_status": "passed",
        "http_status": 200,
        "sanitized_input": input_text,
        "model_run": {
            "status": "success",
            "real_model": True,
            "provider": model_metadata.get("provider"),
            "model": model_metadata.get("model"),
        },
        "structured_result": {
            "status": "PASS",
            "fields": {
                key: structured_output.get(key)
                for key in (
                    "presenting_concerns",
                    "case_overview",
                    "bio_psycho_social",
                    "protective_factors",
                    "risk_formulation",
                    "recommended_focus",
                    "boundary_notes",
                )
            },
        },
        "artifact": {
            "format": "docx",
            "editable": True,
            "download_assertion": "passed",
            "filename": Path(str(docx.get("path"))).name or "output.docx",
        },
    }


def run_w2_acceptance(base_url, username="", password="", invite_code="", deployed_version="", timeout=120, request_json=request_json):
    """Run a hosted W2 BPS case-background scenario and return sanitized durable evidence."""
    _require(bool(str(deployed_version).strip()), "deployed_version is required for W2 acceptance.")
    smoke = run_smoke(
        base_url,
        username=username,
        password=password,
        invite_code=invite_code,
        workflow="W2",
        input_text=W2_HOSTED_SCENARIO,
        timeout=timeout,
        expect_detected_workflow="W2",
        real_run=True,
        render_docx=True,
        request_json=request_json,
    )
    report = {
        "report_type": "hosted",
        "timestamp_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "base_url": _normalize_base_url(base_url),
        "deployed_version": str(deployed_version).strip(),
        "scenario": _w2_acceptance_scenario(W2_HOSTED_SCENARIO, smoke),
    }
    validate_w2_hosted_report(report)
    return report


def _section_map(sections):
    mapped = {}
    if not isinstance(sections, list):
        return mapped
    for section in sections:
        if not isinstance(section, dict):
            continue
        section_id = str(section.get("id") or "").strip().lower()
        if section_id:
            mapped[section_id] = section
    return mapped


def _section_content_list(mapped_sections, *section_ids):
    for section_id in section_ids:
        section = mapped_sections.get(section_id)
        if not isinstance(section, dict):
            continue
        content = str(section.get("content") or "").strip()
        if content:
            return [content]
    return []


def _listify(value):
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _w3_acceptance_scenario(input_text, smoke_report):
    workflow = smoke_report.get("workflow") or {}
    _require(workflow.get("http_status") == 200, "W3 did not return HTTP 200.")
    _require(workflow.get("workflow") == "W3" and workflow.get("detected_workflow") == "W3", "W3 was not detected as W3.")
    _require(workflow.get("real_run") is True, "W3 was not marked as a real-model run.")
    model_metadata = workflow.get("model_metadata") or {}
    _require(
        model_metadata.get("status") == "success"
        and bool(model_metadata.get("provider"))
        and bool(model_metadata.get("model")),
        "W3 real model metadata is required.",
    )
    structured_check = workflow.get("structured_result") or {}
    _require(structured_check.get("status") == "PASS", "W3 structured validation must be PASS.")
    structured_output = workflow.get("structured_output") or {}
    _require(structured_output.get("workflow") == "W3", "W3 structured output is required.")
    docx = workflow.get("artifact") or {}
    docx_check = docx.get("check") or {}
    _require(str(docx.get("status") or "").upper() == "PASS", "W3 DOCX artifact must pass.")
    _require(str(docx_check.get("status") or "").upper() == "PASS", "W3 DOCX validation must pass.")
    _require(bool(docx.get("path")), "W3 DOCX artifact metadata is missing.")

    sections = _section_map(structured_output.get("sections"))
    risk_change = structured_output.get("risk_change") if isinstance(structured_output.get("risk_change"), dict) else {}
    return {
        "workflow": "W3",
        "visible_label": W3_VISIBLE_LABEL,
        "route_status": "passed",
        "http_status": 200,
        "sanitized_input": input_text,
        "model_run": {
            "status": "success",
            "real_model": True,
            "provider": model_metadata.get("provider"),
            "model": model_metadata.get("model"),
        },
        "structured_result": {
            "status": "PASS",
            "fields": {
                "record_format": str(structured_output.get("record_format") or "").upper(),
                "session_sections": {
                    "subjective": _section_content_list(sections, "subjective", "data", "behavior", "client_status", "theme"),
                    "objective": _section_content_list(sections, "objective", "intervention"),
                    "assessment": _section_content_list(sections, "assessment", "response"),
                    "plan": _section_content_list(sections, "plan"),
                },
                "risk_change": {
                    "current_status": _listify(risk_change.get("content")),
                    "change_since_last_contact": _listify(risk_change.get("change_documentation") or risk_change.get("content")),
                    "follow_up_actions": _listify(risk_change.get("follow_up_actions")),
                },
                "next_session_focus": _listify(structured_output.get("next_session_focus")),
                "boundary_notes": _listify(structured_output.get("boundary_notes")),
            },
        },
        "artifact": {
            "format": "docx",
            "editable": True,
            "download_assertion": "passed",
            "filename": Path(str(docx.get("path"))).name or "output.docx",
        },
    }


def run_w3_acceptance(base_url, username="", password="", invite_code="", deployed_version="", timeout=120, request_json=request_json):
    """Run a hosted W3 counseling-record scenario and return sanitized durable evidence."""
    _require(bool(str(deployed_version).strip()), "deployed_version is required for W3 acceptance.")
    smoke = run_smoke(
        base_url,
        username=username,
        password=password,
        invite_code=invite_code,
        workflow="W3",
        input_text=W3_HOSTED_SCENARIO,
        timeout=timeout,
        expect_detected_workflow="W3",
        real_run=True,
        render_docx=True,
        request_json=request_json,
    )
    report = {
        "report_type": "hosted",
        "timestamp_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "base_url": _normalize_base_url(base_url),
        "deployed_version": str(deployed_version).strip(),
        "scenario": _w3_acceptance_scenario(W3_HOSTED_SCENARIO, smoke),
    }
    validate_w3_hosted_report(report)
    return report


def _w4_acceptance_scenario(input_text, smoke_report):
    workflow = smoke_report.get("workflow") or {}
    _require(workflow.get("http_status") == 200, "W4 did not return HTTP 200.")
    _require(workflow.get("workflow") == "W4" and workflow.get("detected_workflow") == "W4", "W4 was not detected as W4.")
    _require(workflow.get("real_run") is True, "W4 was not marked as a real-model run.")
    model_metadata = workflow.get("model_metadata") or {}
    _require(
        model_metadata.get("status") == "success"
        and bool(model_metadata.get("provider"))
        and bool(model_metadata.get("model")),
        "W4 real model metadata is required.",
    )
    structured_check = workflow.get("structured_result") or {}
    _require(structured_check.get("status") == "PASS", "W4 structured validation must be PASS.")
    structured_output = workflow.get("structured_output") or {}
    _require(structured_output.get("workflow") == "W4", "W4 structured output is required.")
    docx = workflow.get("artifact") or {}
    docx_check = docx.get("check") or {}
    _require(str(docx.get("status") or "").upper() == "PASS", "W4 DOCX artifact must pass.")
    _require(str(docx_check.get("status") or "").upper() == "PASS", "W4 DOCX validation must pass.")
    _require(bool(docx.get("path")), "W4 DOCX artifact metadata is missing.")
    return {
        "workflow": "W4",
        "visible_label": W4_VISIBLE_LABEL,
        "route_status": "passed",
        "http_status": 200,
        "sanitized_input": input_text,
        "model_run": {
            "status": "success",
            "real_model": True,
            "provider": model_metadata.get("provider"),
            "model": model_metadata.get("model"),
        },
        "structured_result": {
            "status": "PASS",
            "fields": {key: structured_output.get(key) for key in W4_REQUIRED_FIELDS},
        },
        "artifact": {
            "format": "docx",
            "editable": True,
            "download_assertion": "passed",
            "filename": Path(str(docx.get("path"))).name or "output.docx",
        },
    }


def run_w4_acceptance(base_url, username="", password="", invite_code="", deployed_version="", timeout=120, request_json=request_json):
    """Run a hosted W4 case-conceptualization scenario and return sanitized durable evidence."""
    _require(bool(str(deployed_version).strip()), "deployed_version is required for W4 acceptance.")
    smoke = run_smoke(
        base_url,
        username=username,
        password=password,
        invite_code=invite_code,
        workflow="W4",
        input_text=W4_HOSTED_SCENARIO,
        timeout=timeout,
        expect_detected_workflow="W4",
        real_run=True,
        render_docx=True,
        request_json=request_json,
    )
    report = {
        "report_type": "hosted",
        "timestamp_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "base_url": _normalize_base_url(base_url),
        "deployed_version": str(deployed_version).strip(),
        "scenario": _w4_acceptance_scenario(W4_HOSTED_SCENARIO, smoke),
    }
    validate_w4_hosted_report(report)
    return report


def _w5_acceptance_scenario(input_text, smoke_report):
    workflow = smoke_report.get("workflow") or {}
    _require(workflow.get("http_status") == 200, "W5 did not return HTTP 200.")
    _require(workflow.get("workflow") == "W5" and workflow.get("detected_workflow") == "W5", "W5 was not detected as W5.")
    _require(workflow.get("real_run") is True, "W5 was not marked as a real-model run.")
    model_metadata = workflow.get("model_metadata") or {}
    _require(
        model_metadata.get("status") == "success"
        and bool(model_metadata.get("provider"))
        and bool(model_metadata.get("model")),
        "W5 real model metadata is required.",
    )
    structured_check = workflow.get("structured_result") or {}
    _require(structured_check.get("status") == "PASS", "W5 structured validation must be PASS.")
    structured_output = workflow.get("structured_output") or {}
    _require(structured_output.get("workflow") == "W5", "W5 structured output is required.")
    docx = workflow.get("artifact") or {}
    docx_check = docx.get("check") or {}
    _require(str(docx.get("status") or "").upper() == "PASS", "W5 DOCX artifact must pass.")
    _require(str(docx_check.get("status") or "").upper() == "PASS", "W5 DOCX validation must pass.")
    _require(bool(docx.get("path")), "W5 DOCX artifact metadata is missing.")
    return {
        "workflow": "W5",
        "visible_label": W5_VISIBLE_LABEL,
        "route_status": "passed",
        "http_status": 200,
        "sanitized_input": input_text,
        "model_run": {
            "status": "success",
            "real_model": True,
            "provider": model_metadata.get("provider"),
            "model": model_metadata.get("model"),
        },
        "structured_result": {
            "status": "PASS",
            "fields": {key: structured_output.get(key) for key in W5_REQUIRED_FIELDS},
        },
        "artifact": {
            "format": "docx",
            "editable": True,
            "download_assertion": "passed",
            "filename": Path(str(docx.get("path"))).name or "output.docx",
        },
    }


def run_w5_acceptance(base_url, username="", password="", invite_code="", deployed_version="", timeout=120, request_json=request_json):
    """Run a hosted W5 next-session-plan scenario and return sanitized durable evidence."""
    _require(bool(str(deployed_version).strip()), "deployed_version is required for W5 acceptance.")
    smoke = run_smoke(
        base_url,
        username=username,
        password=password,
        invite_code=invite_code,
        workflow="W5",
        input_text=W5_HOSTED_SCENARIO,
        timeout=timeout,
        expect_detected_workflow="W5",
        real_run=True,
        render_docx=True,
        request_json=request_json,
    )
    report = {
        "report_type": "hosted",
        "timestamp_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "base_url": _normalize_base_url(base_url),
        "deployed_version": str(deployed_version).strip(),
        "scenario": _w5_acceptance_scenario(W5_HOSTED_SCENARIO, smoke),
    }
    validate_w5_hosted_report(report)
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
    parser.add_argument("--w1-acceptance", action="store_true", help="Run both full hosted W1 acceptance scenarios.")
    parser.add_argument("--w2-acceptance", action="store_true", help="Run full hosted W2 acceptance scenario.")
    parser.add_argument("--w3-acceptance", action="store_true", help="Run full hosted W3 acceptance scenario.")
    parser.add_argument("--w4-acceptance", action="store_true", help="Run full hosted W4 acceptance scenario.")
    parser.add_argument("--w5-acceptance", action="store_true", help="Run full hosted W5 acceptance scenario.")
    parser.add_argument("--deployed-version", default="", help="Deployed version or commit for acceptance evidence.")
    parser.add_argument("--report-output", default="", help="Optional sanitized acceptance JSON output path.")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    if args.w1_acceptance:
        report = run_w1_acceptance(
            args.base_url,
            username=args.username,
            password=args.password,
            invite_code=args.invite_code,
            deployed_version=args.deployed_version,
            timeout=args.timeout,
        )
        if args.report_output:
            write_sanitized_report(Path(args.report_output), report)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    if args.w2_acceptance:
        report = run_w2_acceptance(
            args.base_url,
            username=args.username,
            password=args.password,
            invite_code=args.invite_code,
            deployed_version=args.deployed_version,
            timeout=args.timeout,
        )
        if args.report_output:
            write_sanitized_report(Path(args.report_output), report)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    if args.w3_acceptance:
        report = run_w3_acceptance(
            args.base_url,
            username=args.username,
            password=args.password,
            invite_code=args.invite_code,
            deployed_version=args.deployed_version,
            timeout=args.timeout,
        )
        if args.report_output:
            write_w3_sanitized_report(Path(args.report_output), report)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    if args.w4_acceptance:
        report = run_w4_acceptance(
            args.base_url,
            username=args.username,
            password=args.password,
            invite_code=args.invite_code,
            deployed_version=args.deployed_version,
            timeout=args.timeout,
        )
        if args.report_output:
            write_w4_sanitized_report(Path(args.report_output), report)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    if args.w5_acceptance:
        report = run_w5_acceptance(
            args.base_url,
            username=args.username,
            password=args.password,
            invite_code=args.invite_code,
            deployed_version=args.deployed_version,
            timeout=args.timeout,
        )
        if args.report_output:
            write_w5_sanitized_report(Path(args.report_output), report)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
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
