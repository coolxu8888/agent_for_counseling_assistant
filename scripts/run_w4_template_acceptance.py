"""Run strict acceptance against the repository's real W4 conceptualization DOCX."""

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
from w4_acceptance import W4_REQUIRED_FIELDS, W4_TEMPLATE_PATH, validate_template_report, write_sanitized_report


WORD_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
TEXT_TAG = f"{{{WORD_NS}}}t"


class AcceptanceFailure(RuntimeError):
    """The real template did not satisfy the W4 acceptance contract."""


def inspect_template(template_path: Path, repo_root: Path) -> dict:
    root = Path(repo_root).resolve()
    template = Path(template_path).resolve()
    expected = (root / W4_TEMPLATE_PATH).resolve()
    if template != expected or template.suffix.lower() != ".docx":
        raise AcceptanceFailure(f"template must be the repository's real DOCX: {W4_TEMPLATE_PATH}")
    if not template.is_file() or not zipfile.is_zipfile(template):
        raise AcceptanceFailure("template must be a valid real DOCX package")
    try:
        with zipfile.ZipFile(template) as package:
            xml = package.read("word/document.xml")
        ET.fromstring(xml)
    except (KeyError, ET.ParseError, zipfile.BadZipFile) as exc:
        raise AcceptanceFailure("template must contain a valid word/document.xml") from exc
    return {"path": W4_TEMPLATE_PATH, "sha256": hashlib.sha256(template.read_bytes()).hexdigest()}


def _first_text(value, label: str) -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()
    if isinstance(value, list) and value and isinstance(value[0], str) and value[0].strip():
        return value[0].strip()
    raise AcceptanceFailure(f"{label} requires a nonempty text probe")


def _load_structured(structured_path: Path) -> tuple[dict, dict[str, str]]:
    try:
        data = json.loads(Path(structured_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AcceptanceFailure(f"structured result is unreadable: {exc}") from exc
    if data.get("workflow") != "W4" or data.get("document_type") != "case_conceptualization":
        raise AcceptanceFailure("structured result must be a W4 case_conceptualization")
    if data.get("deidentified") is not True:
        raise AcceptanceFailure("acceptance fixture must be explicitly marked deidentified")
    probes = {field: _first_text(data.get(field), field) for field in W4_REQUIRED_FIELDS}
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
        sanitized.append({key: item[key] for key in allowed_keys if key in item and isinstance(item[key], (str, bool, int, float, type(None)))})
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
    allowed_report_dir = (Path(repo_root).resolve() / "eval-results" / "acceptance" / "w4").resolve()
    if report.parent != allowed_report_dir or report.suffix.lower() != ".json":
        raise AcceptanceFailure("report must be a JSON file directly under eval-results/acceptance/w4")
    source = inspect_template(template_path, repo_root)
    _data, probes = _load_structured(structured_path)

    with tempfile.TemporaryDirectory(prefix="w4-template-acceptance-") as tmp:
        tmp_path = Path(tmp)
        output = tmp_path / "filled.docx"
        helper_report_path = tmp_path / "fill-report.json"
        helper_report = fill_helper(Path(template_path), Path(structured_path), output, helper_report_path)
        helper_status = helper_report.get("status") if isinstance(helper_report, dict) else None
        if helper_status == "FAIL":
            raise AcceptanceFailure("shipped template filler reported FAIL")
        if helper_status not in {"PASS", "WARN"}:
            raise AcceptanceFailure("shipped template filler returned an invalid status")
        if not output.is_file():
            raise AcceptanceFailure("shipped template filler did not create a DOCX output")
        reopened_text = _document_text(output)
        verified = {field: probe for field, probe in probes.items() if probe in reopened_text}
        missing = [field for field in W4_REQUIRED_FIELDS if field not in verified]
        if missing:
            raise AcceptanceFailure("filled DOCX is missing canonical W4 content: " + ", ".join(missing))

    report_data = {
        "report_type": "template",
        "timestamp_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "workflow": "W4",
        "source_template": source,
        "fill": {
            "status": helper_status,
            "filled_fields": list(W4_REQUIRED_FIELDS),
            "helper_filled_fields": _sanitize_helper_items(helper_report.get("filled_fields", []), ("template_label", "confidence", "location")),
            "unfilled_fields": _sanitize_helper_items(helper_report.get("unfilled_fields", []), ("template_label", "reason", "location")),
            "issues": _sanitize_helper_items(helper_report.get("issues", []), ("level", "message", "template_label", "location")),
        },
        "output_verification": {"status": "PASS", "reopened": True, "required_content": verified},
    }
    validate_template_report(report_data, Path(repo_root))
    write_sanitized_report(Path(report_path), report_data)
    return report_data


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
        run_template_acceptance(Path(args.template), Path(args.structured_result), Path(args.report), repo_root=Path(args.repo_root))
    except AcceptanceFailure as exc:
        print(f"BLOCKED: {exc}")
        return 1
    print(f"PASS: wrote sanitized report to {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
