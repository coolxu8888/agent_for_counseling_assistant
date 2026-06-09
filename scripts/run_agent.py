import argparse
import json
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from clean_eval_outputs import run_dimension_rubric, run_rule_checks
from run_model_eval import (
    build_chat_payload,
    deepseek_chat_completions_url,
    extract_answer_text,
    load_deepseek_config,
    post_json,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RETRIEVAL_MAP = ROOT / "rag" / "retrieval-map.v0.1.json"
DEFAULT_RUN_ROOT = ROOT / "agent-runs"
DEFAULT_RAG_ROOT = ROOT / "rag"
LOCAL_TIMEZONE = timezone(timedelta(hours=8))


class AgentInputError(ValueError):
    pass


class AgentRunError(RuntimeError):
    pass


@dataclass(frozen=True)
class WorkflowSpec:
    workflow_id: str
    workflow_key: str
    name: str
    eval_id: str
    completion_marker: str


@dataclass(frozen=True)
class AgentRunResult:
    workflow_id: str
    status: str
    run_dir: Path


WORKFLOWS = {
    "W1": WorkflowSpec(
        workflow_id="W1",
        workflow_key="workflow_1_intake_form",
        name="初访信息收集表生成",
        eval_id="W1-001",
        completion_marker="AGENT_DONE_W1",
    ),
    "W2": WorkflowSpec(
        workflow_id="W2",
        workflow_key="workflow_2_case_summary",
        name="个案信息整理",
        eval_id="W2-001",
        completion_marker="AGENT_DONE_W2",
    ),
    "W3": WorkflowSpec(
        workflow_id="W3",
        workflow_key="workflow_3_session_note",
        name="Session 总结与咨询记录生成",
        eval_id="W3-001",
        completion_marker="AGENT_DONE_W3",
    ),
}

WORKFLOW_ALIASES = {
    "w1": "W1",
    "intake": "W1",
    "workflow_1": "W1",
    "workflow_1_intake_form": "W1",
    "w2": "W2",
    "case": "W2",
    "summary": "W2",
    "workflow_2": "W2",
    "workflow_2_case_summary": "W2",
    "w3": "W3",
    "session": "W3",
    "note": "W3",
    "workflow_3": "W3",
    "workflow_3_session_note": "W3",
}

OUTPUT_CONTRACTS = {
    "W1": [
        "标题：初访信息收集表（咨询师访谈版）",
        "必须包含栏目：基本信息、来访原因、当前困扰、生物-心理-社会评估、风险评估、知情同意、咨询师初步记录。",
        "风险评估必须覆盖：自伤、自杀、他伤、物质使用、现实检验、不安全环境、保护因素。",
        "隐私字段要体现最小必要原则，并提示敏感信息可按来访者愿意提供的程度填写。",
        "边界说明必须写入正文：本表不构成诊断，需结合咨询师专业判断。",
    ],
    "W2": [
        "标题：个案信息整理",
        "必须包含栏目：已知事实、主诉与当前困扰、生物维度、心理维度、社会维度、资源与保护因素、风险信号、信息缺口、建议进一步询问的问题。",
        "风险信号栏目必须说明材料中是否见到自伤、自杀、他伤、物质使用、现实检验或不安全环境信息。",
        "若材料未见明确风险信号，必须写：材料中未见明确风险信号，建议咨询师按需进一步评估。",
        "区分事实、推测和待验证内容；未提供的信息写未提供或未提及。",
    ],
    "W3": [
        "标题：本次咨询记录",
        "必须包含栏目：本次主题、来访者状态、关键内容、咨询师干预、来访者反应、风险变化、进展与阻滞、新增个案信息、咨询师判断或初步假设、待补充信息、下次咨询重点、咨询记录正文。",
        "风险变化栏目必须单独列出。若材料未提供风险相关信息，必须写：材料中未提供风险相关信息，建议咨询师按需进一步评估。",
        "未提供的观察、反应或判断不得编造，必须标注材料中未提供或待补充。",
    ],
}


def normalize_workflow(value):
    alias = (value or "").strip().lower()
    workflow_id = WORKFLOW_ALIASES.get(alias)
    if not workflow_id:
        accepted = "W1/intake, W2/case, W3/session"
        raise AgentInputError(f"Unknown workflow `{value}`. Accepted workflows: {accepted}.")
    return WORKFLOWS[workflow_id]


def read_user_input(inline_text, input_file):
    has_inline = inline_text is not None
    has_file = input_file is not None
    if has_inline == has_file:
        raise AgentInputError("Pass exactly one of --input or --input-file.")

    if has_inline:
        text = str(inline_text).strip()
        source = "inline"
    else:
        text = Path(input_file).read_text(encoding="utf-8-sig").strip()
        source = "file"

    if not text:
        raise AgentInputError("User input is empty.")
    return source, text


def load_retrieval_map(path=DEFAULT_RETRIEVAL_MAP):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def selected_chunk_ids_for_workflow(workflow, retrieval_map):
    workflows = retrieval_map.get("workflows", {})
    workflow_config = workflows.get(workflow.workflow_key)
    if not workflow_config:
        raise AgentRunError(f"Workflow `{workflow.workflow_key}` is missing in retrieval map.")

    chunk_ids = []
    for route in workflow_config.get("intent_routes", []):
        for chunk_id in route.get("priority_chunks", []):
            if chunk_id not in chunk_ids:
                chunk_ids.append(chunk_id)
    if not chunk_ids:
        raise AgentRunError(f"No priority chunks configured for {workflow.workflow_key}.")
    return chunk_ids


def _front_matter_chunk_id(text):
    match = re.search(r"(?m)^chunk_id:\s*([A-Za-z0-9_.-]+)\s*$", text)
    return match.group(1) if match else None


def _index_rag_chunks(rag_root):
    index = {}
    for path in Path(rag_root).rglob("*.md"):
        text = path.read_text(encoding="utf-8")
        chunk_id = _front_matter_chunk_id(text)
        if chunk_id:
            index[chunk_id] = {"chunk_id": chunk_id, "path": path, "content": text}
    return index


def load_rag_chunks(chunk_ids, rag_root=DEFAULT_RAG_ROOT):
    index = _index_rag_chunks(rag_root)
    chunks = []
    missing = []
    for chunk_id in chunk_ids:
        chunk = index.get(chunk_id)
        if chunk is None:
            missing.append(chunk_id)
        else:
            chunks.append(chunk)
    if missing:
        raise AgentRunError("Missing RAG chunks: " + ", ".join(missing))
    return chunks


def build_prompt_package(workflow, user_input, rag_chunks):
    rag_sections = []
    for chunk in rag_chunks:
        rag_sections.append(
            "\n".join(
                [
                    f"## Chunk: {chunk['chunk_id']}",
                    f"Path: {chunk['path']}",
                    "",
                    chunk["content"].strip(),
                ]
            )
        )

    return "\n\n".join(
        [
            "# 角色",
            "你是咨询师助理，帮助咨询师整理材料、生成结构化文档和标记信息缺口。你不能替代咨询师诊断、风险分级、危机处置或机构流程。",
            "# 当前 Workflow",
            f"{workflow.workflow_id}: {workflow.name}",
            "# 输出要求",
            "严格基于用户提供的材料作答。未提供的信息写“未提供”“未提及”或“待补充”。风险相关内容需要单独列出。避免确定性诊断措辞。",
            "# Workflow 固定输出结构",
            "\n".join(f"- {line}" for line in OUTPUT_CONTRACTS[workflow.workflow_id]),
            "# RAG 参考资料",
            "\n\n".join(rag_sections),
            "# 用户输入",
            user_input.strip(),
            "# 完成标记",
            f"回答末尾单独输出一行：{workflow.completion_marker}",
        ]
    )


def _isoformat(dt):
    return dt.astimezone(LOCAL_TIMEZONE).isoformat()


def create_run_dir(run_root=DEFAULT_RUN_ROOT, workflow_id="W", now=None):
    timestamp = (now or datetime.now(LOCAL_TIMEZONE)).astimezone(LOCAL_TIMEZONE)
    dirname = timestamp.strftime("%Y-%m-%d-%H%M%S") + f"-{workflow_id}"
    run_dir = Path(run_root) / dirname
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_dir


def write_json(path, data):
    Path(path).write_text(
        json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _safe_error_message(error):
    message = str(error).replace("\r", " ").replace("\n", " ")
    return message[:500]


def _redact_secret(message, secret):
    sanitized = _safe_error_message(message)
    if secret:
        sanitized = sanitized.replace(secret, "[REDACTED]")
    return sanitized


def _metadata_rag_chunks(chunks):
    return [
        {
            "chunk_id": chunk["chunk_id"],
            "path": str(chunk["path"]),
        }
        for chunk in chunks
    ]


def strip_agent_marker(text, workflow):
    lines = []
    for line in text.splitlines():
        normalized = line.strip().strip("*_` ")
        if normalized == workflow.completion_marker:
            break
        lines.append(line)
    return "\n".join(lines).strip() + "\n"


def run_safety_check(workflow, clean_answer):
    rule_result = run_rule_checks(workflow.eval_id, clean_answer)
    rubric_result = run_dimension_rubric(workflow.eval_id, clean_answer)
    return {
        "status": rule_result["status"],
        "rubric_status": rubric_result["status"],
        "missing_required": rule_result["missing_required"],
        "forbidden_hits": rule_result["forbidden_hits"],
        "issues": rubric_result["issues"],
        "dimensions": rubric_result["dimensions"],
    }


def structured_failure(workflow, message, path="structured_output"):
    return {
        "status": "FAIL",
        "workflow": workflow.workflow_id,
        "issues": [
            {
                "level": "ERROR",
                "path": path,
                "message": message,
            }
        ],
    }


def _text_before_marker(text, workflow):
    lines = []
    for line in text.splitlines():
        normalized = line.strip().strip("*_` ")
        if normalized == workflow.completion_marker:
            break
        lines.append(line)
    return "\n".join(lines)


def extract_structured_json(raw_text, workflow):
    text = _text_before_marker(raw_text, workflow)
    blocks = re.findall(r"```json\s*(.*?)\s*```", text, flags=re.IGNORECASE | re.DOTALL)
    if not blocks:
        return None, structured_failure(workflow, "No fenced JSON block found")
    block = blocks[-1]
    try:
        data = json.loads(block)
    except json.JSONDecodeError as exc:
        return None, structured_failure(workflow, f"JSON parse error: {exc}", path="json")
    return data, {"status": "PASS", "workflow": workflow.workflow_id, "issues": []}


def run_agent_once(
    workflow_value,
    inline_input=None,
    input_file=None,
    run_root=DEFAULT_RUN_ROOT,
    run_dir=None,
    retrieval_map_path=DEFAULT_RETRIEVAL_MAP,
    rag_root=DEFAULT_RAG_ROOT,
    dry_run=False,
    no_clean=False,
    model_override=None,
    config=None,
    http_post_json=None,
    now=None,
):
    workflow = normalize_workflow(workflow_value)
    input_source, user_input = read_user_input(inline_input, input_file)
    created_at = now or datetime.now(LOCAL_TIMEZONE)
    output_dir = Path(run_dir) if run_dir else create_run_dir(run_root, workflow.workflow_id, created_at)
    output_dir.mkdir(parents=True, exist_ok=True)

    retrieval_map = load_retrieval_map(retrieval_map_path)
    chunk_ids = selected_chunk_ids_for_workflow(workflow, retrieval_map)
    chunks = load_rag_chunks(chunk_ids, rag_root)
    prompt_package = build_prompt_package(workflow, user_input, chunks)

    write_json(
        output_dir / "input.json",
        {
            "workflow": workflow.workflow_id,
            "workflow_name": workflow.name,
            "input_source": input_source,
            "user_input": user_input,
            "created_at": _isoformat(created_at),
        },
    )
    (output_dir / "prompt_package.txt").write_text(prompt_package, encoding="utf-8")

    if dry_run:
        write_json(
            output_dir / "metadata.json",
            {
                "status": "dry_run",
                "workflow": workflow.workflow_id,
                "workflow_name": workflow.name,
                "selected_rag_chunks": chunk_ids,
                "rag_chunks": _metadata_rag_chunks(chunks),
                "created_at": _isoformat(created_at),
            },
        )
        return AgentRunResult(workflow.workflow_id, "dry_run", output_dir)

    api_config = config or load_deepseek_config()
    if model_override:
        api_config = type(api_config)(
            api_key=api_config.api_key,
            model=model_override,
            base_url=api_config.base_url,
            timeout_seconds=api_config.timeout_seconds,
        )
    http_post_json = http_post_json or post_json
    payload = build_chat_payload(api_config.model, prompt_package)
    url = deepseek_chat_completions_url(api_config.base_url)
    headers = {"Authorization": f"Bearer {api_config.api_key}"}
    started = time.monotonic()

    try:
        response_json = http_post_json(url, headers, payload, api_config.timeout_seconds)
        answer = extract_answer_text(response_json)
    except Exception as exc:
        write_json(
            output_dir / "metadata.json",
            {
                "status": "error",
                "error_type": "api_error",
                "error_message": _redact_secret(exc, api_config.api_key),
                "workflow": workflow.workflow_id,
                "workflow_name": workflow.name,
                "provider": "deepseek",
                "model": api_config.model,
                "selected_rag_chunks": chunk_ids,
                "rag_chunks": _metadata_rag_chunks(chunks),
                "created_at": _isoformat(created_at),
                "latency_seconds": time.monotonic() - started,
            },
        )
        return AgentRunResult(workflow.workflow_id, "error", output_dir)

    (output_dir / "raw_output.txt").write_text(answer.rstrip("\n") + "\n", encoding="utf-8")
    clean_answer = strip_agent_marker(answer, workflow)
    safety_check = None
    if not no_clean:
        (output_dir / "clean_output.md").write_text(clean_answer, encoding="utf-8")
        safety_check = run_safety_check(workflow, clean_answer)
        write_json(output_dir / "safety_check.json", safety_check)

    metadata = {
        "status": "success",
        "workflow": workflow.workflow_id,
        "workflow_name": workflow.name,
        "provider": "deepseek",
        "model": api_config.model,
        "selected_rag_chunks": chunk_ids,
        "rag_chunks": _metadata_rag_chunks(chunks),
        "created_at": _isoformat(created_at),
        "latency_seconds": time.monotonic() - started,
    }
    if "usage" in response_json:
        metadata["usage"] = response_json["usage"]
    if safety_check is not None:
        metadata["safety_status"] = safety_check["status"]
        metadata["rubric_status"] = safety_check["rubric_status"]
    write_json(output_dir / "metadata.json", metadata)
    return AgentRunResult(workflow.workflow_id, "success", output_dir)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Run counselor assistant v0.1 workflows locally.")
    parser.add_argument("--workflow", required=True, help="Workflow: W1/intake, W2/case, W3/session.")
    parser.add_argument("--input", dest="input", default=None, help="Inline user input.")
    parser.add_argument("--input-file", dest="input_file", default=None, help="UTF-8 text/markdown input file.")
    parser.add_argument("--run-root", dest="run_root", default=str(DEFAULT_RUN_ROOT), help="Root folder for timestamped agent runs.")
    parser.add_argument("--run-dir", dest="run_dir", default=None, help="Explicit output folder for this run.")
    parser.add_argument("--retrieval-map", dest="retrieval_map_path", default=str(DEFAULT_RETRIEVAL_MAP), help="Path to retrieval-map JSON.")
    parser.add_argument("--rag-root", dest="rag_root", default=str(DEFAULT_RAG_ROOT), help="Path to RAG root folder.")
    parser.add_argument("--dry-run", action="store_true", help="Build prompt package without calling DeepSeek.")
    parser.add_argument("--no-clean", action="store_true", help="Save raw output only; skip clean output and safety check.")
    parser.add_argument("--model", dest="model", default=None, help="Override DEEPSEEK_MODEL for this run.")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    try:
        result = run_agent_once(
            workflow_value=args.workflow,
            inline_input=args.input,
            input_file=args.input_file,
            run_root=Path(args.run_root),
            run_dir=Path(args.run_dir) if args.run_dir else None,
            retrieval_map_path=Path(args.retrieval_map_path),
            rag_root=Path(args.rag_root),
            dry_run=args.dry_run,
            no_clean=args.no_clean,
            model_override=args.model,
        )
    except AgentInputError as exc:
        print(f"Input error: {exc}", file=sys.stderr)
        return 2
    except (AgentRunError, ValueError) as exc:
        print(f"Run error: {exc}", file=sys.stderr)
        return 1

    print(f"Agent run status: {result.status}")
    print(f"Run directory: {result.run_dir}")
    return 0 if result.status in {"success", "dry_run"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
