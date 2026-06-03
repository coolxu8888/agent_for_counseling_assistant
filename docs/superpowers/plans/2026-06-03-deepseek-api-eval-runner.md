# DeepSeek API Eval Runner Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a DeepSeek `deepseek-v4-flash` API runner that executes existing eval prompts, saves raw/meta results, and automatically runs the existing clean/rubric scoring pipeline.

**Architecture:** Add a focused Python runner for eval selection, config loading, DeepSeek request creation, response parsing, and file persistence. Keep the existing prompt generation and rubric logic as the source of truth, extending the cleaner only enough to recognize API raw result filenames and write summaries into `eval-results/api/`.

**Tech Stack:** Python standard library (`argparse`, `json`, `urllib.request`, `pathlib`, `unittest`, `tempfile`), PowerShell wrapper scripts, existing markdown/json eval fixtures.

---

## File Structure

- Create: `.env.example`
  - Documents local DeepSeek settings.
- Modify: `.gitignore`
  - Ignore `.env` and local secret variants.
- Create: `scripts/run_model_eval.py`
  - Python runner with config loading, eval selection, DeepSeek HTTP call, raw/meta persistence, and optional cleaner handoff.
- Create: `scripts/run-model-eval.ps1`
  - PowerShell wrapper around `scripts/run_model_eval.py`.
- Modify: `scripts/clean_eval_outputs.py`
  - Add raw filename pattern support for `*-deepseek-api-raw.txt`.
- Create: `scripts/test_run_model_eval.py`
  - Unit tests for runner behavior using fake transport.
- Modify: `scripts/test_clean_eval_outputs.py`
  - Add coverage for API raw filename discovery.
- Modify: `README.md`
  - Add the DeepSeek API eval command sequence.

---

## Task 1: Local Secret Configuration

**Files:**
- Create: `.env.example`
- Modify: `.gitignore`

- [ ] **Step 1: Write `.env.example`**

Create `.env.example` with this exact content:

```text
# Copy this file to .env and fill in your local DeepSeek key.
# .env is ignored by git and must not be committed.

DEEPSEEK_API_KEY=
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-v4-flash
DEEPSEEK_TIMEOUT_SECONDS=120
```

- [ ] **Step 2: Ignore local env files**

Append this block to `.gitignore`:

```text

# Local API secrets.
.env
.env.*
!.env.example
```

- [ ] **Step 3: Verify ignore behavior**

Run:

```powershell
"DEEPSEEK_API_KEY=secret" | Set-Content -Encoding UTF8 .env
git status --short
Remove-Item .env
```

Expected:

```text
?? .env.example
 M .gitignore
```

There must be no `.env` line in git status.

- [ ] **Step 4: Commit**

Run:

```powershell
git add .env.example .gitignore
git commit -m "Add DeepSeek eval environment template"
```

---

## Task 2: Runner Selection and Config Tests

**Files:**
- Create: `scripts/test_run_model_eval.py`
- Create: `scripts/run_model_eval.py`

- [ ] **Step 1: Write failing tests for manifest selection and config loading**

Create `scripts/test_run_model_eval.py` with these first tests:

```python
import json
import tempfile
import unittest
from pathlib import Path

from run_model_eval import (
    DeepSeekConfig,
    EvalSelectionError,
    load_deepseek_config,
    load_env_file,
    load_manifest_items,
    select_eval_items,
)


class RunModelEvalTest(unittest.TestCase):
    def test_load_env_file_reads_simple_key_value_pairs(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_path = Path(tmp) / ".env"
            env_path.write_text(
                "DEEPSEEK_API_KEY=abc123\n"
                "DEEPSEEK_MODEL=deepseek-v4-flash\n"
                "# ignored comment\n",
                encoding="utf-8",
            )

            values = load_env_file(env_path)

        self.assertEqual(values["DEEPSEEK_API_KEY"], "abc123")
        self.assertEqual(values["DEEPSEEK_MODEL"], "deepseek-v4-flash")

    def test_load_deepseek_config_defaults_to_v4_flash(self):
        config = load_deepseek_config(
            env_values={"DEEPSEEK_API_KEY": "abc123"},
            process_env={},
        )

        self.assertEqual(
            config,
            DeepSeekConfig(
                api_key="abc123",
                base_url="https://api.deepseek.com",
                model="deepseek-v4-flash",
                timeout_seconds=120,
            ),
        )

    def test_missing_api_key_raises_clear_error(self):
        with self.assertRaisesRegex(ValueError, "DEEPSEEK_API_KEY"):
            load_deepseek_config(env_values={}, process_env={})

    def test_manifest_selection_by_ids_preserves_requested_order(self):
        items = [
            {"id": "W1-001", "prompt_file": "one.txt"},
            {"id": "W3-001", "prompt_file": "three.txt"},
        ]

        selected = select_eval_items(items, ids=["W3-001", "W1-001"], run_all=False)

        self.assertEqual([item["id"] for item in selected], ["W3-001", "W1-001"])

    def test_manifest_selection_rejects_unknown_id(self):
        items = [{"id": "W1-001", "prompt_file": "one.txt"}]

        with self.assertRaisesRegex(EvalSelectionError, "W9-999"):
            select_eval_items(items, ids=["W9-999"], run_all=False)

    def test_load_manifest_items_accepts_list_or_items_object(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest_path = Path(tmp) / "manifest.json"
            manifest_path.write_text(
                json.dumps({"items": [{"id": "W1-001", "prompt_file": "one.txt"}]}),
                encoding="utf-8",
            )

            items = load_manifest_items(manifest_path)

        self.assertEqual(items[0]["id"], "W1-001")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```powershell
python scripts\test_run_model_eval.py
```

Expected:

```text
ModuleNotFoundError: No module named 'run_model_eval'
```

- [ ] **Step 3: Add minimal runner config and selection code**

Create `scripts/run_model_eval.py` with these definitions:

```python
import argparse
import json
import os
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable
from urllib import error, request


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "eval-prompts" / "manifest.json"
DEFAULT_RESULT_DIR = ROOT / "eval-results" / "api"
DEFAULT_ENV_PATH = ROOT / ".env"
DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-v4-flash"
DEFAULT_TIMEOUT_SECONDS = 120


class EvalSelectionError(ValueError):
    pass


@dataclass(frozen=True)
class DeepSeekConfig:
    api_key: str
    base_url: str = DEFAULT_BASE_URL
    model: str = DEFAULT_MODEL
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS


@dataclass(frozen=True)
class EvalRunResult:
    eval_id: str
    status: str
    raw_path: Path | None
    meta_path: Path
    error_type: str | None = None


def load_env_file(path: Path = DEFAULT_ENV_PATH) -> dict[str, str]:
    if not path.exists():
        return {}
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _get_setting(
    key: str,
    env_values: dict[str, str],
    process_env: dict[str, str] | os._Environ[str],
    default: str | None = None,
) -> str | None:
    process_value = process_env.get(key)
    if process_value:
        return process_value
    file_value = env_values.get(key)
    if file_value:
        return file_value
    return default


def load_deepseek_config(
    env_values: dict[str, str] | None = None,
    process_env: dict[str, str] | os._Environ[str] | None = None,
) -> DeepSeekConfig:
    env_values = env_values if env_values is not None else load_env_file()
    process_env = process_env if process_env is not None else os.environ
    api_key = _get_setting("DEEPSEEK_API_KEY", env_values, process_env)
    if not api_key:
        raise ValueError("DEEPSEEK_API_KEY is required. Copy .env.example to .env and set your key.")
    timeout_raw = _get_setting(
        "DEEPSEEK_TIMEOUT_SECONDS",
        env_values,
        process_env,
        str(DEFAULT_TIMEOUT_SECONDS),
    )
    return DeepSeekConfig(
        api_key=api_key,
        base_url=_get_setting("DEEPSEEK_BASE_URL", env_values, process_env, DEFAULT_BASE_URL) or DEFAULT_BASE_URL,
        model=_get_setting("DEEPSEEK_MODEL", env_values, process_env, DEFAULT_MODEL) or DEFAULT_MODEL,
        timeout_seconds=int(timeout_raw or DEFAULT_TIMEOUT_SECONDS),
    )


def load_manifest_items(path: Path = DEFAULT_MANIFEST) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        items = data.get("items", [])
    else:
        items = data
    if not isinstance(items, list):
        raise ValueError("Manifest must be a list or an object with an items list.")
    return items


def select_eval_items(items: list[dict], ids: list[str] | None, run_all: bool) -> list[dict]:
    if run_all:
        return items
    if not ids:
        raise EvalSelectionError("Pass --ids W1-001,W3-001 or --all.")
    by_id = {item["id"]: item for item in items}
    missing = [eval_id for eval_id in ids if eval_id not in by_id]
    if missing:
        raise EvalSelectionError(f"Unknown eval id(s): {', '.join(missing)}")
    return [by_id[eval_id] for eval_id in ids]
```

- [ ] **Step 4: Run tests and verify they pass**

Run:

```powershell
python scripts\test_run_model_eval.py
```

Expected:

```text
Ran 6 tests
OK
```

- [ ] **Step 5: Commit**

Run:

```powershell
git add scripts/run_model_eval.py scripts/test_run_model_eval.py
git commit -m "Add DeepSeek eval runner config tests"
```

---

## Task 3: DeepSeek Request, Dry Run, and File Output

**Files:**
- Modify: `scripts/test_run_model_eval.py`
- Modify: `scripts/run_model_eval.py`

- [ ] **Step 1: Add failing tests for payload, dry-run, success, and error metadata**

Append these tests inside `RunModelEvalTest`:

```python
    def test_build_chat_payload_uses_full_prompt(self):
        from run_model_eval import build_chat_payload

        payload = build_chat_payload("deepseek-v4-flash", "FULL PROMPT")

        self.assertEqual(payload["model"], "deepseek-v4-flash")
        self.assertEqual(payload["messages"], [{"role": "user", "content": "FULL PROMPT"}])
        self.assertEqual(payload["temperature"], 0.2)
        self.assertEqual(payload["max_tokens"], 4096)

    def test_run_eval_dry_run_writes_only_planned_metadata(self):
        from run_model_eval import run_single_eval

        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            root = Path(tmp)
            prompt = root / "prompt.txt"
            prompt.write_text("PROMPT", encoding="utf-8")
            result_dir = root / "results"
            result = run_single_eval(
                item={"id": "W1-001", "prompt_file": str(prompt)},
                config=DeepSeekConfig(api_key="secret"),
                result_dir=result_dir,
                dry_run=True,
                http_post_json=lambda *args, **kwargs: self.fail("HTTP must not be called during dry-run"),
            )

            meta = json.loads(result.meta_path.read_text(encoding="utf-8"))

        self.assertEqual(result.status, "dry_run")
        self.assertIsNone(result.raw_path)
        self.assertEqual(meta["status"], "dry_run")
        self.assertEqual(meta["model"], "deepseek-v4-flash")
        self.assertNotIn("secret", json.dumps(meta))

    def test_run_eval_success_writes_raw_answer_and_metadata(self):
        from run_model_eval import run_single_eval

        calls = []

        def fake_http(url, headers, payload, timeout):
            calls.append((url, headers, payload, timeout))
            return {
                "choices": [{"message": {"content": "ANSWER\nEVAL_DONE_W1_001"}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            }

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            prompt = root / "prompt.txt"
            prompt.write_text("PROMPT", encoding="utf-8")
            result = run_single_eval(
                item={"id": "W1-001", "prompt_file": str(prompt)},
                config=DeepSeekConfig(api_key="secret"),
                result_dir=root / "results",
                dry_run=False,
                http_post_json=fake_http,
            )
            raw_text = result.raw_path.read_text(encoding="utf-8")
            meta = json.loads(result.meta_path.read_text(encoding="utf-8"))

        self.assertEqual(result.status, "success")
        self.assertIn("/chat/completions", calls[0][0])
        self.assertEqual(calls[0][1]["Authorization"], "Bearer secret")
        self.assertEqual(calls[0][2]["messages"][0]["content"], "PROMPT")
        self.assertEqual(raw_text, "ANSWER\nEVAL_DONE_W1_001\n")
        self.assertEqual(meta["status"], "success")
        self.assertEqual(meta["usage"]["total_tokens"], 15)
        self.assertNotIn("secret", json.dumps(meta))

    def test_run_eval_api_error_writes_error_metadata_without_raw_answer(self):
        from run_model_eval import run_single_eval

        def fake_http(url, headers, payload, timeout):
            raise RuntimeError("rate limit reached")

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            prompt = root / "prompt.txt"
            prompt.write_text("PROMPT", encoding="utf-8")
            result = run_single_eval(
                item={"id": "W1-001", "prompt_file": str(prompt)},
                config=DeepSeekConfig(api_key="secret"),
                result_dir=root / "results",
                dry_run=False,
                http_post_json=fake_http,
            )
            meta = json.loads(result.meta_path.read_text(encoding="utf-8"))

        self.assertEqual(result.status, "error")
        self.assertIsNone(result.raw_path)
        self.assertEqual(meta["status"], "error")
        self.assertEqual(meta["error_type"], "api_error")
        self.assertFalse((root / "results" / "W1-001-deepseek-api-raw.txt").exists())
```

- [ ] **Step 2: Run tests and verify they fail on missing functions**

Run:

```powershell
python scripts\test_run_model_eval.py
```

Expected:

```text
ImportError
```

or:

```text
AttributeError
```

for `build_chat_payload` or `run_single_eval`.

- [ ] **Step 3: Add request and persistence code**

Append these functions to `scripts/run_model_eval.py`:

```python
def build_chat_payload(model: str, prompt_text: str) -> dict:
    return {
        "model": model,
        "messages": [{"role": "user", "content": prompt_text}],
        "temperature": 0.2,
        "max_tokens": 4096,
    }


def deepseek_chat_completions_url(base_url: str) -> str:
    return base_url.rstrip("/") + "/chat/completions"


def post_json(url: str, headers: dict[str, str], payload: dict, timeout: int) -> dict:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = request.Request(url, data=body, headers=headers, method="POST")
    try:
        with request.urlopen(req, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"DeepSeek HTTP {exc.code}: {detail[:500]}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"DeepSeek connection error: {exc.reason}") from exc
    return json.loads(raw)


def extract_answer_text(response_json: dict) -> str:
    try:
        return response_json["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError("Malformed DeepSeek response: missing choices[0].message.content") from exc


def _meta_common(eval_id: str, item: dict, config: DeepSeekConfig) -> dict:
    return {
        "eval_id": eval_id,
        "prompt_file": item.get("prompt_file", ""),
        "provider": "deepseek",
        "model": config.model,
        "base_url": config.base_url,
        "has_api_key": bool(config.api_key),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_single_eval(
    item: dict,
    config: DeepSeekConfig,
    result_dir: Path = DEFAULT_RESULT_DIR,
    dry_run: bool = False,
    http_post_json: Callable[[str, dict[str, str], dict, int], dict] = post_json,
) -> EvalRunResult:
    eval_id = item["id"]
    result_dir.mkdir(parents=True, exist_ok=True)
    raw_path = result_dir / f"{eval_id}-deepseek-api-raw.txt"
    meta_path = result_dir / f"{eval_id}-deepseek-api-meta.json"
    prompt_path = Path(item["prompt_file"])
    meta = _meta_common(eval_id, item, config)

    if dry_run:
        meta.update({"status": "dry_run", "planned_raw_file": str(raw_path)})
        _write_json(meta_path, meta)
        return EvalRunResult(eval_id=eval_id, status="dry_run", raw_path=None, meta_path=meta_path)

    prompt_text = prompt_path.read_text(encoding="utf-8")
    payload = build_chat_payload(config.model, prompt_text)
    headers = {
        "Authorization": f"Bearer {config.api_key}",
        "Content-Type": "application/json",
    }
    started = time.monotonic()
    try:
        response_json = http_post_json(
            deepseek_chat_completions_url(config.base_url),
            headers,
            payload,
            config.timeout_seconds,
        )
        answer = extract_answer_text(response_json)
    except ValueError as exc:
        meta.update({"status": "error", "error_type": "malformed_response", "error_message": str(exc)})
        _write_json(meta_path, meta)
        return EvalRunResult(eval_id=eval_id, status="error", raw_path=None, meta_path=meta_path, error_type="malformed_response")
    except Exception as exc:
        meta.update({"status": "error", "error_type": "api_error", "error_message": str(exc)[:500]})
        _write_json(meta_path, meta)
        return EvalRunResult(eval_id=eval_id, status="error", raw_path=None, meta_path=meta_path, error_type="api_error")

    raw_path.write_text(answer.rstrip() + "\n", encoding="utf-8")
    meta.update(
        {
            "status": "success",
            "raw_file": str(raw_path),
            "latency_seconds": round(time.monotonic() - started, 3),
            "usage": response_json.get("usage", {}),
            "finish_reason": response_json.get("choices", [{}])[0].get("finish_reason"),
        }
    )
    _write_json(meta_path, meta)
    return EvalRunResult(eval_id=eval_id, status="success", raw_path=raw_path, meta_path=meta_path)
```

- [ ] **Step 4: Run tests and verify they pass**

Run:

```powershell
python scripts\test_run_model_eval.py
```

Expected:

```text
Ran 10 tests
OK
```

- [ ] **Step 5: Commit**

Run:

```powershell
git add scripts/run_model_eval.py scripts/test_run_model_eval.py
git commit -m "Add DeepSeek eval API call handling"
```

---

## Task 4: Batch CLI and Cleaner Integration

**Files:**
- Modify: `scripts/run_model_eval.py`
- Modify: `scripts/clean_eval_outputs.py`
- Modify: `scripts/test_clean_eval_outputs.py`

- [ ] **Step 1: Add cleaner filename test**

Append this test to `scripts/test_clean_eval_outputs.py`:

```python
    def test_clean_all_supports_deepseek_api_raw_files(self):
        from clean_eval_outputs import clean_all

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result_dir = root / "api"
            clean_dir = result_dir / "clean"
            manifest = root / "manifest.json"
            result_dir.mkdir()
            manifest.write_text(
                json.dumps(
                    [
                        {
                            "id": "W1-001",
                            "name": "intake-counselor-interview",
                            "workflow": "workflow_1_intake_form",
                        }
                    ],
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            (result_dir / "W1-001-deepseek-api-raw.txt").write_text(
                "鍒濊淇℃伅鏀堕泦琛?鍩烘湰淇℃伅 鏉ヨ鍘熷洜 椋庨櫓璇勪及 鐭ユ儏鍚屾剰\nEVAL_DONE_W1_001\n",
                encoding="utf-8",
            )

            rows = clean_all(result_dir, clean_dir, manifest)

        self.assertEqual(rows[0]["id"], "W1-001")
        self.assertEqual(rows[0]["raw_file"], str((result_dir / "W1-001-deepseek-api-raw.txt").relative_to(Path.cwd())))
```

Also add these imports at the top if absent:

```python
import json
import tempfile
from pathlib import Path
```

- [ ] **Step 2: Run cleaner tests and verify the new test fails**

Run:

```powershell
python scripts\test_clean_eval_outputs.py
```

Expected:

```text
FAIL
```

because `clean_all` only searches for `*-deepseek-raw.txt`.

- [ ] **Step 3: Extend cleaner raw discovery**

In `scripts/clean_eval_outputs.py`, replace the loop:

```python
for raw_path in sorted(result_dir.glob("*-deepseek-raw.txt")):
    eval_id = raw_path.name.replace("-deepseek-raw.txt", "")
```

with:

```python
raw_patterns = ["*-deepseek-raw.txt", "*-deepseek-api-raw.txt"]
raw_paths = []
for pattern in raw_patterns:
    raw_paths.extend(result_dir.glob(pattern))

for raw_path in sorted(raw_paths):
    if raw_path.name.endswith("-deepseek-api-raw.txt"):
        eval_id = raw_path.name.replace("-deepseek-api-raw.txt", "")
    else:
        eval_id = raw_path.name.replace("-deepseek-raw.txt", "")
```

- [ ] **Step 4: Add batch runner and cleaner handoff**

Append these functions to `scripts/run_model_eval.py`:

```python
def parse_ids(ids_arg: str | None) -> list[str] | None:
    if not ids_arg:
        return None
    return [part.strip() for part in ids_arg.split(",") if part.strip()]


def run_cleaner(result_dir: Path, manifest_path: Path) -> None:
    import clean_eval_outputs

    rows = clean_eval_outputs.clean_all(result_dir, result_dir / "clean", manifest_path)
    clean_eval_outputs.write_reports(rows, result_dir)


def run_batch(
    items: Iterable[dict],
    config: DeepSeekConfig,
    result_dir: Path,
    dry_run: bool,
    stop_on_error: bool,
    http_post_json: Callable[[str, dict[str, str], dict, int], dict] = post_json,
) -> list[EvalRunResult]:
    results: list[EvalRunResult] = []
    for item in items:
        result = run_single_eval(
            item=item,
            config=config,
            result_dir=result_dir,
            dry_run=dry_run,
            http_post_json=http_post_json,
        )
        results.append(result)
        print(f"{result.eval_id}: {result.status}")
        if stop_on_error and result.status == "error":
            break
    return results


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run counselor-agent eval prompts through DeepSeek API.")
    parser.add_argument("--ids", default=None, help="Comma-separated eval ids, such as W1-001,W3-001.")
    parser.add_argument("--all", action="store_true", help="Run all evals in the manifest.")
    parser.add_argument("--dry-run", action="store_true", help="Validate selection and output paths without calling DeepSeek.")
    parser.add_argument("--no-clean", action="store_true", help="Skip clean/rubric generation after API calls.")
    parser.add_argument("--stop-on-error", action="store_true", help="Stop the batch after the first failed API call.")
    parser.add_argument("--result-dir", default=str(DEFAULT_RESULT_DIR), help="Directory for API eval results.")
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST), help="Eval prompt manifest path.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    manifest_path = Path(args.manifest)
    result_dir = Path(args.result_dir)

    try:
        items = select_eval_items(load_manifest_items(manifest_path), parse_ids(args.ids), args.all)
        config = load_deepseek_config()
    except (EvalSelectionError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    results = run_batch(
        items=items,
        config=config,
        result_dir=result_dir,
        dry_run=args.dry_run,
        stop_on_error=args.stop_on_error,
    )

    if not args.no_clean and not args.dry_run and any(result.status == "success" for result in results):
        run_cleaner(result_dir, manifest_path)
        print(f"Clean/rubric summaries written to {result_dir}")

    if any(result.status == "error" for result in results):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 5: Run tests**

Run:

```powershell
python scripts\test_run_model_eval.py
python scripts\test_clean_eval_outputs.py
```

Expected:

```text
OK
OK
```

- [ ] **Step 6: Commit**

Run:

```powershell
git add scripts/run_model_eval.py scripts/clean_eval_outputs.py scripts/test_clean_eval_outputs.py
git commit -m "Connect API eval runner to cleaner"
```

---

## Task 5: PowerShell Wrapper and Local Smoke Tests

**Files:**
- Create: `scripts/run-model-eval.ps1`
- Modify: `README.md`

- [ ] **Step 1: Add PowerShell wrapper**

Create `scripts/run-model-eval.ps1`:

```powershell
$ErrorActionPreference = "Stop"

param(
    [string]$Ids = "",
    [switch]$All,
    [switch]$DryRun,
    [switch]$NoClean,
    [switch]$StopOnError,
    [string]$ResultDir = "",
    [string]$Manifest = ""
)

$scriptPath = Join-Path $PSScriptRoot "run_model_eval.py"
$argsList = @($scriptPath)

if ($Ids.Trim().Length -gt 0) {
    $argsList += "--ids"
    $argsList += $Ids
}

if ($All) {
    $argsList += "--all"
}

if ($DryRun) {
    $argsList += "--dry-run"
}

if ($NoClean) {
    $argsList += "--no-clean"
}

if ($StopOnError) {
    $argsList += "--stop-on-error"
}

if ($ResultDir.Trim().Length -gt 0) {
    $argsList += "--result-dir"
    $argsList += $ResultDir
}

if ($Manifest.Trim().Length -gt 0) {
    $argsList += "--manifest"
    $argsList += $Manifest
}

python @argsList
exit $LASTEXITCODE
```

- [ ] **Step 2: Run dry-run smoke test**

Create a temporary safe `.env` only for this dry run:

```powershell
"DEEPSEEK_API_KEY=dry-run-key" | Set-Content -Encoding UTF8 .env
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run-model-eval.ps1 -Ids W1-001 -DryRun
Remove-Item .env
```

Expected:

```text
W1-001: dry_run
```

Expected file:

```text
eval-results/api/W1-001-deepseek-api-meta.json
```

Expected absence:

```text
eval-results/api/W1-001-deepseek-api-raw.txt
```

- [ ] **Step 3: Add README commands**

Add this section to `README.md`:

````markdown
## DeepSeek API Eval Runner

Create a local `.env` from `.env.example` and set `DEEPSEEK_API_KEY`.

Dry-run selected evals without spending API credits:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run-model-eval.ps1 -Ids W1-001,W3-001 -DryRun
```

Run selected evals through DeepSeek `deepseek-v4-flash` and automatically generate clean/rubric summaries:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run-model-eval.ps1 -Ids W1-001,W3-001
```

API results are written to:

```text
eval-results/api/
```
````

- [ ] **Step 4: Commit**

Run:

```powershell
git add scripts/run-model-eval.ps1 README.md
git commit -m "Add DeepSeek eval PowerShell runner"
```

---

## Task 6: Final Verification and Optional Real API Eval

**Files:**
- No required code changes.
- Optional generated files: `eval-results/api/*`

- [ ] **Step 1: Run full non-network verification**

Run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\validate-rag.ps1
python scripts\test_clean_eval_outputs.py
python scripts\test_run_model_eval.py
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run-model-eval.ps1 -Ids W1-001 -DryRun
```

Expected:

```text
RAG validation PASS
OK
OK
W1-001: dry_run
```

- [ ] **Step 2: Confirm no API key is tracked**

Run:

```powershell
git status --short
git ls-files .env
```

Expected:

```text
```

for `git ls-files .env`.

- [ ] **Step 3: Optional real API smoke test**

Only run this if the user has added a real local `.env` with `DEEPSEEK_API_KEY`.

Run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run-model-eval.ps1 -Ids W1-001
```

Expected:

```text
W1-001: success
Clean/rubric summaries written to C:\Users\win\Documents\Codex\2026-05-15\agent\eval-results\api
```

Expected files:

```text
eval-results/api/W1-001-deepseek-api-raw.txt
eval-results/api/W1-001-deepseek-api-meta.json
eval-results/api/clean/W1-001-clean.md
eval-results/api/eval-clean-summary.v0.1.md
eval-results/api/eval-rubric-summary.v0.1.md
```

- [ ] **Step 4: Review generated API result files before committing**

If real API eval files were generated, inspect:

```powershell
Get-Content eval-results\api\W1-001-deepseek-api-meta.json
Get-Content eval-results\api\eval-rubric-summary.v0.1.md
```

Confirm:

- Metadata contains no API key.
- Raw output is a real model answer.
- Rubric summary points to API clean output paths.

- [ ] **Step 5: Commit final verification-related edits**

If only code/docs changed:

```powershell
git status --short
git add .
git commit -m "Verify DeepSeek API eval runner"
```

If real API generated outputs should stay local, do not commit `eval-results/api/` files unless the user explicitly wants to keep them as fixtures.

---

## Plan Self-Review

Spec coverage:

- DeepSeek-specific runner: Task 2, Task 3, Task 4, Task 5.
- Default `deepseek-v4-flash`: Task 1, Task 2, Task 3.
- `.env.example` and secret safety: Task 1, Task 6.
- Selected eval ids from manifest: Task 2.
- Raw/meta output under `eval-results/api/`: Task 3.
- Automatic clean/rubric handoff: Task 4.
- Dry-run mode: Task 3, Task 5, Task 6.
- Fake transport tests with no real API call: Task 3.
- Existing validation remains passing: Task 6.

Ambiguity resolved:

- API runner sends each full eval prompt as a single user message because prompt files already include system rules, RAG context, task input, and eval marker.
- API results stay separate from historical Web eval files.
- Real API generated outputs are not committed unless the user asks to preserve them as fixtures.
