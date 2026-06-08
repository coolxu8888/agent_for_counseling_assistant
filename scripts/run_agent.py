import argparse
import json
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RETRIEVAL_MAP = ROOT / "rag" / "retrieval-map.v0.1.json"
DEFAULT_RUN_ROOT = ROOT / "agent-runs"
DEFAULT_RAG_ROOT = ROOT / "rag"


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
            "# RAG 参考资料",
            "\n\n".join(rag_sections),
            "# 用户输入",
            user_input.strip(),
            "# 完成标记",
            f"回答末尾单独输出一行：{workflow.completion_marker}",
        ]
    )
