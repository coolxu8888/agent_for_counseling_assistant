"""Run strict acceptance against the repository's real W1 summary DOCX."""

from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable
from xml.etree import ElementTree as ET

from fill_docx_template import fill_docx_template
from w1_acceptance import (
    W1_SUMMARY_SECTIONS,
    W1_TEMPLATE_PATH,
    validate_template_report,
    write_sanitized_report,
)


WORD_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
TEXT_TAG = f"{{{WORD_NS}}}t"


class AcceptanceFailure(RuntimeError):
    """The real template did not satisfy the W1 acceptance contract."""


def inspect_template(template_path: Path, repo_root: Path) -> dict:
    root = Path(repo_root).resolve()
    template = Path(template_path).resolve()
    expected = (root / W1_TEMPLATE_PATH).resolve()
    if template != expected or template.suffix.lower() != ".docx":
        raise AcceptanceFailure(f"template must be the repository's real DOCX: {W1_TEMPLATE_PATH}")
    if not template.is_file() or not zipfile.is_zipfile(template):
        raise AcceptanceFailure("template must be a valid real DOCX package")
    try:
        with zipfile.ZipFile(template) as package:
            xml = package.read("word/document.xml")
        ET.fromstring(xml)
    except (KeyError, ET.ParseError, zipfile.BadZipFile) as exc:
        raise AcceptanceFailure("template must contain a valid word/document.xml") from exc
    return {
        "path": W1_TEMPLATE_PATH,
        "sha256": hashlib.sha256(template.read_bytes()).hexdigest(),
    }


def _load_sections(structured_path: Path) -> tuple[dict, dict[str, str]]:
    try:
        data = json.loads(Path(structured_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AcceptanceFailure(f"structured result is unreadable: {exc}") from exc
    if data.get("workflow") != "W1" or data.get("document_type") != "initial_session_summary":
        raise AcceptanceFailure("structured result must be a W1 initial_session_summary")
    if data.get("deidentified") is not True:
        raise AcceptanceFailure("acceptance fixture must be explicitly marked deidentified")
    sections = data.get("sections")
    if not isinstance(sections, list):
        raise AcceptanceFailure("structured result sections are required")
    by_id = {item.get("id"): item for item in sections if isinstance(item, dict)}
    if set(by_id) != set(W1_SUMMARY_SECTIONS) or len(sections) != len(W1_SUMMARY_SECTIONS):
        raise AcceptanceFailure("structured result must contain every canonical W1 summary section exactly once")
    probes = {}
    for section_id in W1_SUMMARY_SECTIONS:
        facts = by_id[section_id].get("known_facts")
        if not isinstance(facts, list) or not facts or not isinstance(facts[0], str) or not facts[0].strip():
            raise AcceptanceFailure(f"canonical section {section_id} requires nonempty known_facts")
        probes[section_id] = facts[0].strip()
    return data, probes


def _document_text(docx_path: Path) -> str:
    try:
        with zipfile.ZipFile(docx_path) as package:
            root = ET.fromstring(package.read("word/document.xml"))
    except (OSError, KeyError, ET.ParseError, zipfile.BadZipFile) as exc:
        raise AcceptanceFailure("filled output could not be reopened as DOCX") from exc
    return "\n".join((node.text or "") for node in root.iter(TEXT_TAG))


def _sanitize_helper_items(items, allowed_keys: tuple[str, ...]) -> list[dict]:
    if not isinstance(items, list):
        return []
    sanitized = []
    for item in items:
        if not isinstance(item, dict):
            continue
        clean = {
            key: item[key]
            for key in allowed_keys
            if key in item and isinstance(item[key], (str, bool, int, float, type(None)))
        }
        sanitized.append(clean)
    return sanitized


def run_template_acceptance(
    template_path: Path,
    structured_path: Path,
    report_path: Path,
    *,
    repo_root: Path,
    fill_helper: Callable = fill_docx_template,
) -> dict:
    report = Path(report_path).resolve()
    allowed_report_dir = (Path(repo_root).resolve() / "eval-results" / "acceptance" / "w1").resolve()
    if report.parent != allowed_report_dir or report.suffix.lower() != ".json":
        raise AcceptanceFailure("report must be a JSON file directly under eval-results/acceptance/w1")
    source = inspect_template(template_path, repo_root)
    _data, probes = _load_sections(structured_path)

    with tempfile.TemporaryDirectory(prefix="w1-template-acceptance-") as tmp:
        tmp_path = Path(tmp)
        output = tmp_path / "filled.docx"
        helper_report_path = tmp_path / "fill-report.json"
        helper_report = fill_helper(
            Path(template_path), Path(structured_path), output, helper_report_path
        )
        helper_status = helper_report.get("status") if isinstance(helper_report, dict) else None
        if helper_status == "FAIL":
            raise AcceptanceFailure("shipped template filler reported FAIL")
        if helper_status not in {"PASS", "WARN"}:
            raise AcceptanceFailure("shipped template filler returned an invalid status")
        if not output.is_file():
            raise AcceptanceFailure("shipped template filler did not create a DOCX output")
        reopened_text = _document_text(output)
        verified = {
            section_id: probe
            for section_id, probe in probes.items()
            if probe in reopened_text
        }
        missing = [section_id for section_id in W1_SUMMARY_SECTIONS if section_id not in verified]
        if missing:
            raise AcceptanceFailure(
                "filled DOCX is missing canonical mapped content: " + ", ".join(missing)
            )

    helper_filled = _sanitize_helper_items(
        helper_report.get("filled_fields", []),
        ("template_label", "source_path", "confidence", "location"),
    )
    unfilled = _sanitize_helper_items(
        helper_report.get("unfilled_fields", []),
        ("template_label", "reason", "location"),
    )
    issues = _sanitize_helper_items(
        helper_report.get("issues", []),
        ("level", "message", "template_label", "location"),
    )
    report = {
        "report_type": "template",
        "timestamp_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "workflow": "W1",
        "mode": "initial_interview_summary",
        "source_template": source,
        "fill": {
            "status": helper_status,
            "filled_fields": list(W1_SUMMARY_SECTIONS),
            "helper_filled_fields": helper_filled,
            "unfilled_fields": unfilled,
            "issues": issues,
        },
        "output_verification": {
            "status": "PASS",
            "reopened": True,
            "required_sections": verified,
        },
    }
    validate_template_report(report, Path(repo_root))
    write_sanitized_report(Path(report_path), report)
    return report


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--template", required=True)
    parser.add_argument("--structured-result", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--repo-root", default=str(Path(__file__).resolve().parents[1]))
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    try:
        run_template_acceptance(
            Path(args.template),
            Path(args.structured_result),
            Path(args.report),
            repo_root=Path(args.repo_root),
        )
    except AcceptanceFailure as exc:
        print(f"BLOCKED: {exc}")
        return 1
    print(f"PASS: wrote sanitized report to {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
