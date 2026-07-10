"""Validation and safe, deterministic writing for committed W4 evidence."""

from __future__ import annotations

import hashlib
import ipaddress
import json
import math
import re
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


W4_VISIBLE_LABEL = "个案概念化"
W4_TEMPLATE_PATH = "docs/w4-case-conceptualization-template.docx"
W4_REQUIRED_FIELDS = (
    "selected_framework",
    "known_facts",
    "presenting_patterns",
    "predisposing_factors",
    "precipitating_factors",
    "maintaining_factors",
    "protective_factors",
    "risk_considerations",
    "working_hypotheses",
    "questions_to_verify",
    "boundary_notes",
)
W4_FRAMEWORKS = {"CBT", "PSYCHODYNAMIC", "HUMANISTIC", "INTEGRATIVE"}


class W4AcceptanceError(ValueError):
    """Raised when a report cannot serve as durable W4 evidence."""


_SENSITIVE_VALUE = re.compile(
    r"(?:\b(?:authorization|cookie|set-cookie)\s*:|\bbearer\s+[A-Za-z0-9._~+/=-]+|\bsk-[A-Za-z0-9_-]+|"
    r"\b(?:(?:[a-z0-9]+[_-])*(?:password|token|session|cookie|secret|credentials?)"
    r"|api(?:[ _-]+)key|private(?:[ _-]+)key)(?:[_-][a-z0-9]+)*\s*[:=]\s*\S)",
    re.IGNORECASE,
)
_CREDENTIALED_URL = re.compile(r"https?://[^\s/@:]+:[^\s/@]+@", re.IGNORECASE)
_JWT = re.compile(r"(?<![A-Za-z0-9_-])[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}(?![A-Za-z0-9_-])")
_WINDOWS_DRIVE_PATH = re.compile(r"(?<![A-Za-z0-9])[A-Za-z]:[\\/]+[^\s,;)\]}]+")
_WINDOWS_UNC_PATH = re.compile(r"(?<![A-Za-z0-9_\\])\\\\[^\\/\s]+[\\/][^\s,;)\]}]+")
_UNIX_ABSOLUTE_PATH = re.compile(r"(?<![A-Za-z0-9:/])(/[A-Za-z0-9._~-]+(?:/[A-Za-z0-9._~-]+)+)")
_REPEATED_UNIX_SEPARATOR = re.compile(r"(?<!:)/{2,}")
_HTTP_ROUTE_PREFIX = re.compile(r"^\s*(?:DELETE|GET|HEAD|OPTIONS|PATCH|POST|PUT)\s+", re.IGNORECASE)


def _fail(message: str) -> None:
    raise W4AcceptanceError(message)


def _require(condition: bool, message: str) -> None:
    if not condition:
        _fail(message)


def _key_tokens(key: str) -> list[str]:
    snake = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", key)
    return re.findall(r"[a-z0-9]+", snake.lower())


def _is_sensitive_key(key: str) -> bool:
    tokens = _key_tokens(key)
    if any(tokens[index : index + 2] in (["api", "key"], ["private", "key"]) for index in range(len(tokens) - 1)):
        return True
    sensitive = {"authorization", "cookie", "cookies", "credential", "credentials", "password", "passwords", "secret", "secrets", "session", "sessions", "token", "tokens"}
    indices = [index for index, token in enumerate(tokens) if token in sensitive]
    if not indices:
        return False
    telemetry_suffixes = {"count", "counts", "length", "total"}
    return not all(index + 1 == len(tokens) - 1 and tokens[-1] in telemetry_suffixes for index in indices)


def _contains_absolute_filesystem_path(value: str, location: str) -> bool:
    if _WINDOWS_DRIVE_PATH.search(value) or _WINDOWS_UNC_PATH.search(value):
        return True
    repeated_separator = bool(_REPEATED_UNIX_SEPARATOR.search(value))
    normalized = _REPEATED_UNIX_SEPARATOR.sub("/", value)
    route_field = bool(re.search(r"(?:^|\.)(?:routes?|endpoints?)(?:\[|\.|$)", location, re.IGNORECASE))
    method_route = bool(_HTTP_ROUTE_PREFIX.match(normalized))
    for match in _UNIX_ABSOLUTE_PATH.finditer(normalized):
        candidate = match.group(1)
        segments = candidate.split("/")[1:]
        safe_segments = all(segment not in {".", ".."} for segment in segments)
        route_shaped = route_field or method_route or candidate.startswith("/api/") or candidate.startswith("/health/")
        if not repeated_separator and route_shaped and safe_segments:
            continue
        return True
    return repeated_separator


def _validate_sanitized(value: Any, location: str = "report") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            _require(isinstance(key, str), f"{location} contains a non-string key")
            if _is_sensitive_key(key):
                _fail(f"{location}.{key} is a forbidden secret or cookie field")
            _validate_sanitized(child, f"{location}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _validate_sanitized(child, f"{location}[{index}]")
    elif isinstance(value, str):
        if _SENSITIVE_VALUE.search(value) or _CREDENTIALED_URL.search(value) or _JWT.search(value):
            _fail(f"{location} contains secret or cookie material")
        if _contains_absolute_filesystem_path(value, location):
            _fail(f"{location} contains a direct server filesystem path")
    elif isinstance(value, float) and not math.isfinite(value):
        _fail(f"{location} contains a non-finite number")
    elif value is not None and not isinstance(value, (bool, int, float)):
        _fail(f"{location} contains unsupported data type {type(value).__name__}")


def _validate_timestamp(value: Any) -> None:
    _require(isinstance(value, str) and value.endswith("Z"), "timestamp_utc must be an ISO UTC timestamp ending in Z")
    try:
        datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        _fail("timestamp_utc must be a valid ISO UTC timestamp")


def _validate_url(value: Any, *, hosted: bool) -> None:
    _require(isinstance(value, str), "base_url must be a URL")
    parsed = urlparse(value)
    expected_scheme = ("https",) if hosted else ("http", "https")
    _require(parsed.scheme in expected_scheme and bool(parsed.netloc), "hosted base_url must be a valid public HTTPS URL" if hosted else "base_url must be an HTTP URL")
    _require(parsed.username is None and parsed.password is None, "base_url must not contain URL userinfo credentials")
    if not hosted:
        return
    host = (parsed.hostname or "").lower()
    try:
        parsed.port
    except ValueError:
        _fail("hosted base_url must use a valid public host")
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


def _require_nonempty_list(value: Any, location: str) -> None:
    _require(
        isinstance(value, list) and any(isinstance(item, str) and item.strip() for item in value),
        f"{location} must contain at least one meaningful item",
    )


def _validate_w4_fields(fields: Any) -> None:
    _require(isinstance(fields, dict), "structured_result.fields must be an object")
    for field in W4_REQUIRED_FIELDS:
        _require(field in fields, f"structured_result.fields.{field} is required")
    framework = str(fields.get("selected_framework") or "").upper()
    _require(framework in W4_FRAMEWORKS, "selected_framework must be CBT, psychodynamic, humanistic, or integrative")
    for field in W4_REQUIRED_FIELDS:
        if field == "selected_framework":
            continue
        _require_nonempty_list(fields.get(field), field)


def _validate_artifact(value: Any, location: str) -> None:
    _require(isinstance(value, dict), f"{location}.artifact metadata is required")
    _require(value.get("format") == "docx", f"{location}.artifact must be DOCX")
    _require(value.get("editable") is True, f"{location}.artifact must be editable")
    _require(value.get("download_assertion") == "passed", f"{location}.artifact download assertion must pass")
    filename = value.get("filename")
    _require(isinstance(filename, str) and filename.lower().endswith(".docx"), f"{location}.artifact filename must be DOCX")


def _validate_scenario(scenario: Any) -> None:
    _require(isinstance(scenario, dict), "scenario must be an object")
    _require(scenario.get("workflow") == "W4", "scenario.workflow must be W4")
    _require(scenario.get("visible_label") == W4_VISIBLE_LABEL, "scenario.visible_label must be the Chinese W4 conceptualization label")
    _require(scenario.get("route_status") == "passed", "scenario.route_status must pass")
    structured = scenario.get("structured_result")
    _require(isinstance(structured, dict) and structured.get("status") == "PASS", "scenario.structured_result must pass")
    _validate_w4_fields(structured.get("fields"))
    _validate_artifact(scenario.get("artifact"), "scenario")


def _validate_base(report: dict, report_type: str) -> dict:
    _require(isinstance(report, dict), "report must be an object")
    _validate_sanitized(report)
    _require(report.get("report_type") == report_type, f"report_type must be {report_type}")
    _validate_timestamp(report.get("timestamp_utc"))
    scenario = report.get("scenario")
    _validate_scenario(scenario)
    return scenario


def validate_web_report(report: dict) -> None:
    """Validate visible local Web acceptance evidence for W4."""
    _validate_base(report, "web")
    _validate_url(report.get("base_url"), hosted=False)


def validate_hosted_report(report: dict) -> None:
    """Validate offline URL form plus full W4 hosted HTTP/model evidence."""
    scenario = _validate_base(report, "hosted")
    _validate_url(report.get("base_url"), hosted=True)
    version = report.get("deployed_version")
    _require(isinstance(version, str) and bool(version.strip()), "deployed_version is required")
    _require(scenario.get("http_status") == 200, "scenario must record a real HTTP 200 response")
    model_run = scenario.get("model_run")
    _require(
        isinstance(model_run, dict)
        and model_run.get("status") == "success"
        and model_run.get("real_model") is True
        and bool(model_run.get("provider"))
        and bool(model_run.get("model")),
        "scenario.model_run must prove a successful real-model run",
    )
    sanitized_input = scenario.get("sanitized_input")
    _require(isinstance(sanitized_input, str) and bool(sanitized_input.strip()), "scenario.sanitized_input is required")


def validate_template_report(report: dict, repo_root: Path) -> None:
    """Validate evidence from filling and reopening the repository's real W4 DOCX."""
    _require(isinstance(report, dict), "report must be an object")
    _validate_sanitized(report)
    _require(report.get("report_type") == "template", "report_type must be template")
    _validate_timestamp(report.get("timestamp_utc"))
    _require(report.get("workflow") == "W4", "workflow must be W4")

    source = report.get("source_template")
    _require(isinstance(source, dict), "source_template identity is required")
    relative = source.get("path")
    _require(relative == W4_TEMPLATE_PATH, f"source_template.path must identify {W4_TEMPLATE_PATH}")
    root = Path(repo_root).resolve()
    template = (root / relative).resolve()
    _require(template.is_relative_to(root), "resolved source template must remain inside repo_root")
    _require(template.is_file(), "source template must be the real repository W4 DOCX")
    expected_hash = source.get("sha256")
    _require(isinstance(expected_hash, str) and len(expected_hash) == 64, "source_template.sha256 is required")
    _require(hashlib.sha256(template.read_bytes()).hexdigest() == expected_hash.lower(), "source_template.sha256 does not match the real template")

    fill = report.get("fill")
    _require(isinstance(fill, dict), "fill results are required")
    filled_fields = fill.get("filled_fields")
    _require(
        isinstance(filled_fields, list)
        and set(filled_fields) == set(W4_REQUIRED_FIELDS)
        and len(filled_fields) == len(W4_REQUIRED_FIELDS),
        "filled_fields must cover every canonical W4 field",
    )
    _require(isinstance(fill.get("unfilled_fields"), list), "unfilled_fields must be recorded")
    _require(isinstance(fill.get("issues"), list), "issues must be recorded")

    verification = report.get("output_verification")
    _require(isinstance(verification, dict), "output_verification is required")
    _require(verification.get("status") == "PASS" and verification.get("reopened") is True, "filled output must be reopened and pass")
    required = verification.get("required_content")
    _require(isinstance(required, dict) and set(required) == set(W4_REQUIRED_FIELDS), "required_content must cover every canonical W4 field")
    for field, value in required.items():
        _require(isinstance(value, str) and len(value.strip()) >= 2, f"required_content.{field} must contain meaningful mapped content")


def validate_model_eval_report(report: dict, repo_root: Path) -> None:
    """Validate committed W4 real-model evaluation evidence without contacting external services."""
    _require(isinstance(report, dict), "report must be an object")
    _validate_sanitized(report)
    _require(report.get("report_type") == "real_model_eval", "report_type must be real_model_eval")
    _validate_timestamp(report.get("timestamp_utc"))
    _require(report.get("workflow") == "W4", "workflow must be W4")
    _require(report.get("rubric_status") == "PASS", "rubric_status must be PASS")
    cases = report.get("eval_cases")
    _require(isinstance(cases, list) and any(str(case).startswith("W4-") for case in cases), "eval_cases must include W4 cases")
    model_run = report.get("model_run")
    _require(
        isinstance(model_run, dict)
        and model_run.get("status") == "success"
        and model_run.get("real_model") is True
        and bool(model_run.get("provider"))
        and bool(model_run.get("model")),
        "model_run must prove a successful real-model run",
    )
    structured = report.get("structured_result")
    _require(isinstance(structured, dict) and structured.get("status") == "PASS", "structured_result must pass")
    _validate_w4_fields(structured.get("fields"))
    evidence = report.get("evidence")
    _require(isinstance(evidence, list) and evidence, "evidence must be non-empty")
    root = Path(repo_root).resolve()
    for index, item in enumerate(evidence):
        _require(isinstance(item, dict), f"evidence[{index}] must be an object")
        _require(item.get("type") == "path", f"evidence[{index}].type must be path")
        value = item.get("value")
        _require(isinstance(value, str) and value.startswith("eval-results/"), f"evidence[{index}] must point under eval-results")
        target = (root / value).resolve()
        _require(target.is_relative_to(root) and target.is_file(), f"evidence[{index}] path does not exist")


def write_sanitized_report(path: Path, report: dict) -> None:
    """Write sanitized JSON with stable key order, formatting, encoding, and newline."""
    _require(isinstance(report, dict), "report must be an object")
    _validate_sanitized(report)
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n"
    destination.write_text(payload, encoding="utf-8", newline="\n")
