import argparse
import json
from pathlib import Path

from fill_docx_template import fill_docx_template_with_llm_mapping
from run_model_eval import DeepSeekConfig, load_deepseek_config, post_json
from render_docx import write_docx_package


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "eval-prompts" / "template-fill-manifest.json"
DEFAULT_RESULT_DIR = ROOT / "eval-results" / "template-fill"


def load_template_fill_eval_items(path):
    manifest_path = Path(path)
    items = json.loads(manifest_path.read_text(encoding="utf-8"))
    resolved = []
    for item in items:
        resolved_item = dict(item)
        for key in ("template_xml_file", "structured_output_file"):
            value = resolved_item.get(key)
            if value:
                candidate = Path(value)
                if not candidate.is_absolute():
                    resolved_item[key] = str((manifest_path.parent / candidate).resolve())
        resolved.append(resolved_item)
    return resolved


def _score_template_fill(item, report, mapping, output_text):
    expected_source_path = item.get("expected_source_path")
    expected_label = item.get("expected_label")
    expected_output_contains = item.get("expected_output_contains") or []

    issues = []
    mapped_item = None
    for candidate in mapping.get("mappings", []):
        if expected_label and candidate.get("template_label") == expected_label:
            mapped_item = candidate
            break
    if expected_source_path and (not mapped_item or mapped_item.get("source_path") != expected_source_path):
        issues.append(f"Expected source path {expected_source_path} for label {expected_label or '<any>'}.")
    for needle in expected_output_contains:
        if needle not in output_text:
            issues.append(f"Expected output to contain: {needle}")
    if report.get("status") == "FAIL":
        issues.append("Template fill report returned FAIL.")
    if report.get("llm_status") not in {"success", "skipped"}:
        issues.append(f"Unexpected llm_status: {report.get('llm_status')}")
    status = "PASS" if not issues else "FAIL"
    return {"status": status, "issues": issues}


def run_single_template_fill_eval(item, config: DeepSeekConfig, result_dir, http_post_json=post_json):
    eval_id = item["id"]
    target_dir = Path(result_dir) / eval_id
    target_dir.mkdir(parents=True, exist_ok=True)

    template_xml = Path(item["template_xml_file"]).read_text(encoding="utf-8")
    structured_output = Path(item["structured_output_file"]).read_text(encoding="utf-8")

    template_path = target_dir / "template.docx"
    structured_path = target_dir / "structured_output.json"
    output_path = target_dir / "filled_template.docx"
    report_path = target_dir / "template_fill_report.json"
    mapping_path = target_dir / "template_mapping.json"
    meta_path = target_dir / f"{eval_id}-template-fill-eval.json"

    write_docx_package(template_path, template_xml)
    structured_path.write_text(structured_output, encoding="utf-8")
    report = fill_docx_template_with_llm_mapping(
        template_path,
        structured_path,
        output_path,
        report_path,
        mapping_output_path=mapping_path,
        config=config,
        http_post_json=http_post_json,
    )
    mapping = json.loads(mapping_path.read_text(encoding="utf-8")) if mapping_path.exists() else {"mappings": []}
    with Path(output_path).open("rb"):
        pass
    from zipfile import ZipFile

    with ZipFile(output_path, "r") as package:
        output_text = package.read("word/document.xml").decode("utf-8")

    score = _score_template_fill(item, report, mapping, output_text)
    result = {
        "id": eval_id,
        "name": item.get("name", eval_id),
        "status": score["status"],
        "issues": score["issues"],
        "report": report,
        "mapping": mapping,
        "output_path": str(output_path),
        "report_path": str(report_path),
        "mapping_path": str(mapping_path),
    }
    meta_path.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def parse_ids(ids_arg):
    if not ids_arg:
        return None
    return [part.strip() for part in ids_arg.split(",") if part.strip()]


def select_items(items, ids=None, run_all=False):
    if run_all:
        return list(items)
    if not ids:
        raise ValueError("Pass --ids ID[,ID...] or --all.")
    by_id = {item["id"]: item for item in items}
    selected = []
    for eval_id in ids:
        if eval_id not in by_id:
            raise ValueError(f"Unknown template fill eval id: {eval_id}")
        selected.append(by_id[eval_id])
    return selected


def build_arg_parser():
    parser = argparse.ArgumentParser(description="Run template fill evals with real DOCX fixtures.")
    parser.add_argument("--ids")
    parser.add_argument("--all", action="store_true", dest="run_all")
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--result-dir", default=str(DEFAULT_RESULT_DIR))
    return parser


def main(argv=None):
    args = build_arg_parser().parse_args(argv)
    try:
        items = load_template_fill_eval_items(args.manifest)
        selected = select_items(items, ids=parse_ids(args.ids), run_all=args.run_all)
        config = load_deepseek_config()
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(str(exc))
        return 2

    failures = 0
    for item in selected:
        result = run_single_template_fill_eval(item, config, args.result_dir)
        print(f"{result['id']}: {result['status']}")
        if result["status"] != "PASS":
            failures += 1
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
