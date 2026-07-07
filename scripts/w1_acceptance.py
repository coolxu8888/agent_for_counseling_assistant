"""Validation and safe, deterministic writing for committed W1 evidence."""

from __future__ import annotations

import hashlib
import ipaddress
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


W1_MODES = ("intake_prep", "initial_interview_summary")
W1_VISIBLE_LABELS = {
    "intake_prep": "初始访谈准备",
    "initial_interview_summary": "初始访谈总结",
}
W1_TEMPLATE_PATH = "docs/4.心理咨询初始访谈表_20210906.docx"
W1_SUMMARY_SECTIONS = (
    "main_distress",
    "basic_situation",
    "functioning",
    "support_coping",
    "history",
    "psychological_tests",
    "risk_crisis",
    "handling_suggestion",
    "other_notes",
)


class W1AcceptanceError(ValueError):
    """Raised when a report cannot serve as durable W1 evidence."""


_SENSITIVE_KEY = re.compile(
    r"(?:^|_)(?:api_key|authorization|cookies?|credentials?|passwords?|private_key|secrets?|sessions?|tokens?)(?:_|$)",
    re.IGNORECASE,
)
_SENSITIVE_VALUE = re.compile(
    r"(?:\b(?:authorization|cookie|set-cookie)\s*:|\bbearer\s+[A-Za-z0-9._~+/=-]+|\bsk-[A-Za-z0-9_-]+|"
    r"\b(?:[a-z0-9]+_)*(?:password|token|session|cookie)(?:_[a-z0-9]+)*\s*[:=]\s*\S)",
    re.IGNORECASE,
)
_DIRECT_PATH = re.compile(r"(?:^|\s)(?:/[A-Za-z0-9_.-]|[A-Za-z]:[\\/]|\\\\)[^\s]*")


def _fail(message: str) -> None:
    raise W1AcceptanceError(message)


def _require(condition: bool, message: str) -> None:
    if not condition:
        _fail(message)


def _validate_sanitized(value: Any, location: str = "report") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            _require(isinstance(key, str), f"{location} contains a non-string key")
            if _SENSITIVE_KEY.search(key):
                _fail(f"{location}.{key} is a forbidden secret or cookie field")
            _validate_sanitized(child, f"{location}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _validate_sanitized(child, f"{location}[{index}]")
    elif isinstance(value, str):
        if _SENSITIVE_VALUE.search(value):
            _fail(f"{location} contains secret or cookie material")
        if _DIRECT_PATH.search(value):
            _fail(f"{location} contains a direct server filesystem path")
    elif value is not None and not isinstance(value, (bool, int, float)):
        _fail(f"{location} contains unsupported data type {type(value).__name__}")


def _validate_timestamp(value: Any) -> None:
    _require(isinstance(value, str) and value.endswith("Z"), "timestamp_utc must be an ISO UTC timestamp ending in Z")
    try:
        datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        _fail("timestamp_utc must be a valid ISO UTC timestamp")


def _validate_base(report: dict, report_type: str) -> list[dict]:
    _require(isinstance(report, dict), "report must be an object")
    _validate_sanitized(report)
    _require(report.get("report_type") == report_type, f"report_type must be {report_type}")
    _validate_timestamp(report.get("timestamp_utc"))
    scenarios = report.get("scenarios")
    _require(isinstance(scenarios, list), "scenarios must be a list")
    modes = [item.get("mode") for item in scenarios if isinstance(item, dict)]
    _require(len(scenarios) == len(W1_MODES) and set(modes) == set(W1_MODES), "report must cover both W1 modes exactly once")
    return scenarios


def _validate_url(value: Any, *, hosted: bool) -> None:
    _require(isinstance(value, str), "base_url must be a URL")
    parsed = urlparse(value)
    expected_scheme = ("https",) if hosted else ("http", "https")
    _require(parsed.scheme in expected_scheme and bool(parsed.netloc), "base_url must be a valid public HTTPS URL" if hosted else "base_url must be an HTTP URL")
    if hosted:
        host = (parsed.hostname or "").lower()
        _require(parsed.username is None and parsed.password is None, "hosted base_url must be public and contain no user information")
        try:
            parsed.port
        except ValueError:
            _fail("hosted base_url must be a valid public URL")
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            labels = host.split(".")
            public_form = (
                len(labels) >= 2
                and all(re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label) for label in labels)
                and bool(re.fullmatch(r"[a-z]{2,63}", labels[-1]))
                and not host.endswith((".invalid", ".test", ".example", ".localhost", ".local", ".internal"))
            )
            _require(public_form, "hosted base_url must use a public host form")
        else:
            _require(address.is_global, "hosted base_url must use a public IP address")


def _validate_artifact(value: Any, location: str) -> None:
    _require(isinstance(value, dict), f"{location}.artifact metadata is required")
    _require(value.get("format") == "docx", f"{location}.artifact must be DOCX")
    _require(value.get("editable") is True, f"{location}.artifact must be editable")
    _require(value.get("download_assertion") == "passed", f"{location}.artifact download assertion must pass")
    filename = value.get("filename")
    _require(isinstance(filename, str) and filename.lower().endswith(".docx"), f"{location}.artifact filename must be DOCX")


def _validate_scenario(scenario: Any, index: int) -> None:
    location = f"scenarios[{index}]"
    _require(isinstance(scenario, dict), f"{location} must be an object")
    _require(scenario.get("workflow") == "W1", f"{location}.workflow must be W1")
    mode = scenario.get("mode")
    _require(mode in W1_MODES, f"{location}.mode is invalid")
    label = scenario.get("visible_label")
    _require(label == W1_VISIBLE_LABELS[mode], f"{location}.visible_label must be the mode-specific Chinese label")
    _require(scenario.get("route_status") == "passed", f"{location}.route_status must pass")
    structured = scenario.get("structured_result")
    _require(isinstance(structured, dict) and structured.get("status") == "PASS", f"{location}.structured_result must pass")
    sections = structured.get("sections")
    _require(isinstance(sections, (list, dict)) and len(sections) > 0, f"{location}.structured_result sections are required")
    _validate_artifact(scenario.get("artifact"), location)


def validate_web_report(report: dict) -> None:
    """Validate visible, two-mode local Web acceptance evidence."""
    scenarios = _validate_base(report, "web")
    _validate_url(report.get("base_url"), hosted=False)
    for index, scenario in enumerate(scenarios):
        _validate_scenario(scenario, index)


def validate_hosted_report(report: dict) -> None:
    """Validate full hosted real-model evidence, not route-only smoke output."""
    scenarios = _validate_base(report, "hosted")
    _validate_url(report.get("base_url"), hosted=True)
    version = report.get("deployed_version")
    _require(isinstance(version, str) and bool(version.strip()), "deployed_version is required")
    for index, scenario in enumerate(scenarios):
        _validate_scenario(scenario, index)
        model_run = scenario.get("model_run")
        _require(
            isinstance(model_run, dict)
            and model_run.get("status") == "success"
            and model_run.get("real_model") is True,
            f"scenarios[{index}].model_run must prove a successful real-model run",
        )
        sanitized_input = scenario.get("sanitized_input")
        _require(isinstance(sanitized_input, str) and bool(sanitized_input.strip()), f"scenarios[{index}].sanitized_input is required")


def validate_template_report(report: dict, repo_root: Path) -> None:
    """Validate evidence from filling and reopening the repository's real W1 template."""
    _require(isinstance(report, dict), "report must be an object")
    _validate_sanitized(report)
    _require(report.get("report_type") == "template", "report_type must be template")
    _validate_timestamp(report.get("timestamp_utc"))
    _require(report.get("workflow") == "W1", "workflow must be W1")
    _require(report.get("mode") == "initial_interview_summary", "template mode must be initial_interview_summary")

    source = report.get("source_template")
    _require(isinstance(source, dict), "source_template identity is required")
    relative = source.get("path")
    _require(relative == W1_TEMPLATE_PATH, f"source_template.path must identify {W1_TEMPLATE_PATH}")
    root = Path(repo_root).resolve()
    template = (root / relative).resolve()
    _require(template.is_file(), "source template must be the real repository W1 DOCX")
    expected_hash = source.get("sha256")
    _require(isinstance(expected_hash, str) and len(expected_hash) == 64, "source_template.sha256 is required")
    _require(hashlib.sha256(template.read_bytes()).hexdigest() == expected_hash.lower(), "source_template.sha256 does not match the real template")

    fill = report.get("fill")
    _require(isinstance(fill, dict), "fill results are required")
    filled_fields = fill.get("filled_fields")
    _require(
        isinstance(filled_fields, list)
        and len(filled_fields) == len(W1_SUMMARY_SECTIONS)
        and set(filled_fields) == set(W1_SUMMARY_SECTIONS),
        "filled_fields must cover every canonical W1 summary section",
    )
    _require(isinstance(fill.get("unfilled_fields"), list), "unfilled_fields must be recorded")
    _require(isinstance(fill.get("issues"), list), "issues must be recorded")

    verification = report.get("output_verification")
    _require(isinstance(verification, dict), "output_verification is required")
    _require(verification.get("status") == "PASS" and verification.get("reopened") is True, "filled output must be reopened and pass")
    sections = verification.get("required_sections")
    _require(
        isinstance(sections, dict)
        and set(sections) == set(W1_SUMMARY_SECTIONS)
        and all(isinstance(value, str) and len(value.strip()) >= 2 for value in sections.values()),
        "all canonical W1 summary sections must contain meaningful mapped content",
    )


def write_sanitized_report(path: Path, report: dict) -> None:
    """Write sanitized JSON with stable key order, formatting, encoding, and newline."""
    _require(isinstance(report, dict), "report must be an object")
    _validate_sanitized(report)
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    destination.write_text(payload, encoding="utf-8", newline="\n")
