"""Validate and render the derived W1-W6 completion matrix."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence
from urllib.parse import urlsplit


WORKFLOW_IDS = tuple(f"W{index}" for index in range(1, 7))
GATE_IDS = (
    "local_tests",
    "real_model_eval",
    "web_integration",
    "hosted_verification",
    "real_template_verification",
)
VALID_STATUSES = {"passed", "failed", "unverified"}
START_MARKER = "<!-- workflow-completion:start -->"
END_MARKER = "<!-- workflow-completion:end -->"


class CompletionValidationError(ValueError):
    """Raised when completion data or its generated document is invalid."""


def load_matrix(path: Path) -> dict:
    """Load a JSON completion matrix."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CompletionValidationError(f"cannot load matrix {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise CompletionValidationError("matrix root must be an object")
    return data


def _require_exact_keys(actual: object, expected: tuple[str, ...], label: str) -> None:
    if not isinstance(actual, dict) or set(actual) != set(expected):
        found = sorted(actual) if isinstance(actual, dict) else type(actual).__name__
        raise CompletionValidationError(
            f"{label} must be exactly {list(expected)}; found {found}"
        )


def _contains_key(value: object, forbidden: str) -> bool:
    if isinstance(value, dict):
        return forbidden in value or any(
            _contains_key(item, forbidden) for item in value.values()
        )
    if isinstance(value, list):
        return any(_contains_key(item, forbidden) for item in value)
    return False


def validate_matrix(data: dict, repo_root: Path) -> None:
    """Reject schema drift, unsupported claims, and missing evidence."""
    if not isinstance(data, dict):
        raise CompletionValidationError("matrix root must be an object")
    if data.get("schema_version") != 1:
        raise CompletionValidationError("schema_version must be 1")
    workflows = data.get("workflows")
    _require_exact_keys(workflows, WORKFLOW_IDS, "workflow keys")
    root = repo_root.resolve()

    for workflow_id in WORKFLOW_IDS:
        workflow = workflows[workflow_id]
        if not isinstance(workflow, dict):
            raise CompletionValidationError(f"{workflow_id} must be an object")
        if _contains_key(workflow, "completed"):
            raise CompletionValidationError(
                f"{workflow_id} must not store a completed field anywhere"
            )
        if not isinstance(workflow.get("name"), str) or not workflow["name"].strip():
            raise CompletionValidationError(f"{workflow_id}.name must be non-empty")
        gates = workflow.get("gates")
        _require_exact_keys(gates, GATE_IDS, f"{workflow_id} gate keys")

        for gate_id in GATE_IDS:
            gate = gates[gate_id]
            if not isinstance(gate, dict):
                raise CompletionValidationError(
                    f"{workflow_id}.{gate_id} must be an object"
                )
            status = gate.get("status")
            if status not in VALID_STATUSES:
                raise CompletionValidationError(
                    f"{workflow_id}.{gate_id} has unsupported status {status!r}"
                )
            evidence = gate.get("evidence")
            if not isinstance(evidence, list):
                raise CompletionValidationError(
                    f"{workflow_id}.{gate_id}.evidence must be a list"
                )
            if status == "passed" and not evidence:
                raise CompletionValidationError(
                    f"{workflow_id}.{gate_id} needs non-empty evidence when passed"
                )
            for index, item in enumerate(evidence):
                prefix = f"{workflow_id}.{gate_id}.evidence[{index}]"
                if not isinstance(item, dict):
                    raise CompletionValidationError(f"{prefix} must be an object")
                evidence_type = item.get("type")
                value = item.get("value")
                if evidence_type not in {"path", "command", "url"}:
                    raise CompletionValidationError(
                        f"{prefix}.type must be 'path', 'command', or 'url'"
                    )
                if not isinstance(value, str) or not value.strip():
                    raise CompletionValidationError(f"{prefix}.value must be non-empty")
                if evidence_type == "path":
                    candidate = (root / value).resolve()
                    try:
                        candidate.relative_to(root)
                    except ValueError as exc:
                        raise CompletionValidationError(
                            f"{prefix} points outside repository: {value}"
                        ) from exc
                    if not candidate.exists():
                        raise CompletionValidationError(
                            f"{prefix} path does not exist: {value}"
                        )
                elif evidence_type == "url":
                    parsed = urlsplit(value)
                    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                        raise CompletionValidationError(
                            f"{prefix} must be an absolute HTTP(S) URL"
                        )


def derive_workflow_status(workflow: dict) -> dict:
    """Derive completion and ordered missing gates from validated workflow data."""
    missing = [
        gate_id
        for gate_id in GATE_IDS
        if workflow["gates"][gate_id]["status"] != "passed"
    ]
    return {"completed": not missing, "missing_gates": missing}


def render_markdown(data: dict) -> str:
    """Render a compact Chinese table from validated matrix data."""
    headers = ["工作流", "名称", *GATE_IDS, "总体状态", "首个缺失门槛"]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    labels = {"passed": "通过", "failed": "失败", "unverified": "未验证"}
    for workflow_id in WORKFLOW_IDS:
        workflow = data["workflows"][workflow_id]
        derived = derive_workflow_status(workflow)
        statuses = [labels[workflow["gates"][gate_id]["status"]] for gate_id in GATE_IDS]
        overall = "完成" if derived["completed"] else "未完成"
        first_missing = derived["missing_gates"][0] if derived["missing_gates"] else "—"
        row = [workflow_id, workflow["name"], *statuses, overall, first_missing]
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def replace_generated_section(document: str, rendered: str) -> str:
    """Replace only content inside the two completion markers."""
    if document.count(START_MARKER) != 1 or document.count(END_MARKER) != 1:
        raise CompletionValidationError(
            "document must contain exactly one ordered pair of completion markers"
        )
    start = document.index(START_MARKER) + len(START_MARKER)
    end = document.index(END_MARKER)
    if start > end:
        raise CompletionValidationError("completion markers are out of order")
    return document[:start] + "\n" + rendered.rstrip("\n") + "\n" + document[end:]


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="fail if generated content is stale")
    mode.add_argument("--write", action="store_true", help="regenerate marked content")
    repo_root = Path(__file__).resolve().parents[1]
    parser.add_argument("--matrix", type=Path, default=repo_root / "workflow-completion.json")
    parser.add_argument(
        "--document", type=Path, default=repo_root / "docs" / "product-loop-state.md"
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Check for generated-document drift or write regenerated content."""
    args = _parser().parse_args(argv)
    try:
        data = load_matrix(args.matrix)
        validate_matrix(data, args.matrix.resolve().parent)
        document = args.document.read_text(encoding="utf-8")
        expected = replace_generated_section(document, render_markdown(data))
        if args.check:
            if expected != document:
                print(
                    "workflow completion matrix is stale; regenerate with "
                    "python scripts/workflow_completion.py --write",
                    file=sys.stderr,
                )
                return 1
            return 0
        args.document.write_text(expected, encoding="utf-8")
        return 0
    except (CompletionValidationError, OSError) as exc:
        print(
            f"workflow completion check failed: {exc}; regenerate with "
            "python scripts/workflow_completion.py --write",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
