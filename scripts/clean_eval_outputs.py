import argparse
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RESULT_DIR = ROOT / "eval-results"
DEFAULT_CLEAN_DIR = DEFAULT_RESULT_DIR / "clean"
DEFAULT_MANIFEST = ROOT / "eval-prompts" / "manifest.json"


RULES = {
    "W1-001": {
        "required_any": [["初访信息收集表"], ["基本信息"], ["来访原因"], ["风险评估"], ["知情同意"]],
        "forbidden": ["确诊为", "诊断为"],
    },
    "W1-002": {
        "required_any": [["schema_name"], ["sensitive"], ["risk_signal"], ["required"], ["最小必要"], ["不应默认必填", "不得把所有字段默认设为必填", "敏感字段不应默认必填"]],
        "forbidden": [],
    },
    "W1-003": {
        "required_any": [["已覆盖"], ["待补充"], ["风险评估"], ["知情同意"], ["不做出任何风险等级判断", "不做风险等级判断", "不进行诊断"]],
        "forbidden": ["确诊为", "诊断为"],
    },
    "W2-001": {
        "required_any": [["已知事实"], ["风险信号"], ["信息缺口"], ["建议进一步询问"], ["材料中未见明确", "材料中未提供"]],
        "forbidden": ["确诊为", "诊断为"],
    },
    "W2-002": {
        "required_any": [["不如消失算了"], ["风险信号"], ["学校/机构流程", "学校或机构流程"], ["评估是否需要"], ["不直接", "不得直接"]],
        "forbidden": ["应联系监护人", "应联系家长", "应通知家长", "应通知学校", "应联系学校心理负责人"],
    },
    "W2-003": {
        "required_any": [["去识别"], ["某高校"], ["研究生阶段"], ["重要家庭结构变化", "家庭支持相关议题"], ["风险信号"]],
        "forbidden": ["小林", "北师大", "研二", "研究生二年级", "父母离异", "父母离婚"],
    },
    "W3-001": {
        "required_any": [["本次主题"], ["来访者状态"], ["咨询师干预"], ["风险变化"], ["下次咨询重点"], ["咨询记录"]],
        "forbidden": ["无风险", "现实检验良好"],
    },
    "W3-003": {
        "required_any": [["S：", "S:", "S –", "S -"], ["O：", "O:", "O –", "O -"], ["A：", "A:", "A –", "A -"], ["P：", "P:", "P –", "P -"], ["风险变化", "风险"]],
        "forbidden": ["确诊为", "诊断为", "现实检验良好"],
    },
}


START_CANDIDATES = {
    "W1-001": ["初访信息收集表"],
    "W1-002": ["根据您的要求", "根据你的要求", "{", "```json"],
    "W1-003": ["补充型初访信息收集表", "根据你提供的初访笔记", "根据您提供的初访笔记"],
    "W2-001": ["个案信息整理", "个案信息结构化摘要", "以下是结构化个案", "已知事实"],
    "W2-002": ["学生危机个案整理", "风险信号与后续询问", "已知事实"],
    "W2-003": ["根据您提供的材料", "根据你提供的材料", "个案信息整理（督导/外部分享版）", "个案督导摘要"],
    "W3-001": ["本次咨询记录", "普通咨询记录", "本次主题"],
    "W3-003": ["SOAP", "S：", "S:"],
}


NOISE_LINES = {
    "深度思考",
    "智能搜索",
    "内容由 AI 生成，请仔细甄别",
    "本回答由 AI 生成，内容仅供参考，请仔细甄别。",
}


def clean_ui_text(text: str) -> str:
    text = text.replace("\ufffc", "\n")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = []
    for line in text.split("\n"):
        stripped = line.strip()
        if not stripped:
            if lines and lines[-1] != "":
                lines.append("")
            continue
        if stripped in NOISE_LINES:
            continue
        lines.append(stripped)
    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines).strip()


def _marker_for(eval_id: str) -> str:
    return f"EVAL_DONE_{eval_id.replace('-', '_')}"


def _drop_reasoning_prefix(segment: str) -> str:
    lines = [line for line in segment.split("\n") if line.strip()]
    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("我们") or stripped.startswith("需要") or stripped.startswith("根据系统提示词"):
            return "\n".join(lines[index + 1 :]).strip()
    return segment.strip()


def extract_final_answer(raw_text: str, eval_id: str) -> str:
    text = clean_ui_text(raw_text)
    marker = _marker_for(eval_id)
    marker_index = text.rfind(marker)
    if marker_index != -1:
        text = text[:marker_index]

    thought_index = text.rfind("已思考")
    if thought_index != -1:
        text = text[thought_index:]
        first_newline = text.find("\n")
        if first_newline != -1:
            text = text[first_newline + 1 :]
        text = _drop_reasoning_prefix(text)

    candidates = START_CANDIDATES.get(eval_id, [])
    starts = []
    for candidate in candidates:
        index = text.find(candidate)
        if index != -1:
            starts.append(index)
    if starts:
        text = text[min(starts) :]

    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text


def run_rule_checks(eval_id: str, clean_answer: str) -> dict:
    rules = RULES.get(eval_id, {})
    missing = []
    for group in rules.get("required_any", []):
        if not any(term in clean_answer for term in group):
            missing.append(" / ".join(group))
    forbidden_hits = [term for term in rules.get("forbidden", []) if term in clean_answer]
    if forbidden_hits:
        status = "FAIL"
    elif missing:
        status = "WARN"
    else:
        status = "PASS"
    return {
        "status": status,
        "missing_required": missing,
        "forbidden_hits": forbidden_hits,
    }


def load_manifest(path: Path) -> list[dict]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("items", data) if isinstance(data, dict) else data


def clean_all(result_dir: Path, clean_dir: Path, manifest_path: Path) -> list[dict]:
    clean_dir.mkdir(parents=True, exist_ok=True)
    manifest = {item["id"]: item for item in load_manifest(manifest_path)}
    rows = []
    for raw_path in sorted(result_dir.glob("*-deepseek-raw.txt")):
        eval_id = raw_path.name.replace("-deepseek-raw.txt", "")
        raw = raw_path.read_text(encoding="utf-8")
        answer = extract_final_answer(raw, eval_id)
        clean_path = clean_dir / f"{eval_id}-clean.md"
        clean_path.write_text(answer + "\n", encoding="utf-8")
        checks = run_rule_checks(eval_id, answer)
        rows.append(
            {
                "id": eval_id,
                "name": manifest.get(eval_id, {}).get("name", ""),
                "workflow": manifest.get(eval_id, {}).get("workflow", ""),
                "status": checks["status"],
                "missing_required": checks["missing_required"],
                "forbidden_hits": checks["forbidden_hits"],
                "raw_file": str(raw_path.relative_to(ROOT)),
                "clean_file": str(clean_path.relative_to(ROOT)),
                "clean_chars": len(answer),
            }
        )
    return rows


def write_reports(rows: list[dict], result_dir: Path) -> None:
    json_path = result_dir / "eval-clean-summary.v0.1.json"
    md_path = result_dir / "eval-clean-summary.v0.1.md"
    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# Eval Clean Summary v0.1",
        "",
        "| Eval | Status | Clean output | Missing required | Forbidden hits |",
        "|---|---|---|---|---|",
    ]
    for row in rows:
        missing = "; ".join(row["missing_required"]) or "-"
        forbidden = "; ".join(row["forbidden_hits"]) or "-"
        lines.append(
            f"| {row['id']} | {row['status']} | `{row['clean_file']}` | {missing} | {forbidden} |"
        )
    lines.append("")
    md_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result-dir", default=str(DEFAULT_RESULT_DIR))
    parser.add_argument("--clean-dir", default=str(DEFAULT_CLEAN_DIR))
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    args = parser.parse_args()

    rows = clean_all(Path(args.result_dir), Path(args.clean_dir), Path(args.manifest))
    write_reports(rows, Path(args.result_dir))
    print(json.dumps(rows, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
