import argparse
import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_DEEPSEEK_MODEL = "deepseek-v4-flash"
DEFAULT_DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEFAULT_DEEPSEEK_TIMEOUT = 120
ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ENV_PATH = ROOT / ".env"
DEFAULT_RESULT_DIR = ROOT / "eval-results" / "api"
DEFAULT_MANIFEST = ROOT / "eval-prompts" / "manifest.json"


class EvalSelectionError(ValueError):
    pass


@dataclass(frozen=True)
class DeepSeekConfig:
    api_key: str
    model: str = DEFAULT_DEEPSEEK_MODEL
    base_url: str = DEFAULT_DEEPSEEK_BASE_URL
    timeout_seconds: int = DEFAULT_DEEPSEEK_TIMEOUT


@dataclass(frozen=True)
class EvalRunResult:
    eval_id: str
    status: str
    raw_path: Path | None
    meta_path: Path


def load_env_file(path):
    env_path = Path(path)
    values = {}
    if not env_path.exists():
        return values

    for raw_line in env_path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key:
            values[key] = value.strip()
    return values


def build_chat_payload(model, prompt_text):
    return {
        "model": model,
        "messages": [{"role": "user", "content": prompt_text}],
        "temperature": 0.2,
        "max_tokens": 4096,
    }


def deepseek_chat_completions_url(base_url):
    return base_url.rstrip("/") + "/chat/completions"


def _safe_error_message(error):
    message = str(error).replace("\r", " ").replace("\n", " ")
    return message[:500]


def post_json(url, headers, payload, timeout):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={**headers, "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            response_body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"HTTP {exc.code}: {_safe_error_message(exc.reason)}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"URL error: {_safe_error_message(exc.reason)}") from exc

    return json.loads(response_body)


def extract_answer_text(response_json):
    try:
        answer = response_json["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError("Malformed DeepSeek response: missing choices[0].message.content") from exc
    if not isinstance(answer, str):
        raise ValueError("Malformed DeepSeek response: choices[0].message.content is not text")
    return answer


def _write_meta(path, meta):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(meta, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _sanitize_for_metadata(message, config):
    sanitized = _safe_error_message(message)
    if config.api_key:
        sanitized = sanitized.replace(config.api_key, "[REDACTED]")
    return sanitized


def _base_meta(config):
    return {
        "model": config.model,
        "provider": "deepseek",
        "has_api_key": bool(config.api_key),
    }


def _finish_reason(response_json):
    try:
        return response_json["choices"][0].get("finish_reason")
    except (KeyError, IndexError, TypeError, AttributeError):
        return None


def run_single_eval(item, config, result_dir, dry_run=False, http_post_json=post_json):
    eval_id = item["id"]
    prompt_path = Path(item["prompt_file"])
    result_path = Path(result_dir)
    raw_path = result_path / f"{eval_id}-deepseek-api-raw.txt"
    meta_path = result_path / f"{eval_id}-deepseek-api-meta.json"

    if dry_run:
        _write_meta(
            meta_path,
            {
                **_base_meta(config),
                "status": "dry_run",
                "planned_raw_file": str(raw_path),
            },
        )
        return EvalRunResult(eval_id=eval_id, status="dry_run", raw_path=None, meta_path=meta_path)

    prompt_text = prompt_path.read_text(encoding="utf-8")
    payload = build_chat_payload(config.model, prompt_text)
    url = deepseek_chat_completions_url(config.base_url)
    headers = {"Authorization": f"Bearer {config.api_key}"}
    started = time.monotonic()
    created_at = datetime.now(timezone.utc).isoformat()

    try:
        response_json = http_post_json(url, headers, payload, config.timeout_seconds)
        answer = extract_answer_text(response_json)
    except ValueError as exc:
        _write_meta(
            meta_path,
            {
                **_base_meta(config),
                "status": "error",
                "error_type": "malformed_response",
                "error_message": _sanitize_for_metadata(exc, config),
                "base_url": config.base_url,
                "created_at": created_at,
                "latency_seconds": time.monotonic() - started,
            },
        )
        return EvalRunResult(eval_id=eval_id, status="error", raw_path=None, meta_path=meta_path)
    except Exception as exc:
        _write_meta(
            meta_path,
            {
                **_base_meta(config),
                "status": "error",
                "error_type": "api_error",
                "error_message": _sanitize_for_metadata(exc, config),
                "base_url": config.base_url,
                "created_at": created_at,
                "latency_seconds": time.monotonic() - started,
            },
        )
        return EvalRunResult(eval_id=eval_id, status="error", raw_path=None, meta_path=meta_path)

    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text(answer.rstrip("\n") + "\n", encoding="utf-8")
    meta = {
        **_base_meta(config),
        "status": "success",
        "raw_file": str(raw_path),
        "model": config.model,
        "base_url": config.base_url,
        "created_at": created_at,
        "latency_seconds": time.monotonic() - started,
    }
    if "usage" in response_json:
        meta["usage"] = response_json["usage"]
    finish_reason = _finish_reason(response_json)
    if finish_reason is not None:
        meta["finish_reason"] = finish_reason
    _write_meta(meta_path, meta)
    return EvalRunResult(eval_id=eval_id, status="success", raw_path=raw_path, meta_path=meta_path)


def _get_config_value(env_values, name, default=None):
    return os.environ.get(name) or env_values.get(name) or default


def load_deepseek_config(env_values=None):
    file_values = load_env_file(DEFAULT_ENV_PATH) if env_values is None else env_values
    api_key = _get_config_value(file_values, "DEEPSEEK_API_KEY")
    if not api_key:
        raise ValueError("Missing DEEPSEEK_API_KEY for DeepSeek API evaluation runner")

    timeout_value = _get_config_value(
        file_values, "DEEPSEEK_TIMEOUT_SECONDS", str(DEFAULT_DEEPSEEK_TIMEOUT)
    )
    return DeepSeekConfig(
        api_key=api_key,
        model=_get_config_value(file_values, "DEEPSEEK_MODEL", DEFAULT_DEEPSEEK_MODEL),
        base_url=_get_config_value(
            file_values, "DEEPSEEK_BASE_URL", DEFAULT_DEEPSEEK_BASE_URL
        ),
        timeout_seconds=int(timeout_value),
    )


def load_manifest_items(path):
    manifest_path = Path(path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if isinstance(manifest, list):
        items = manifest
    elif isinstance(manifest, dict) and isinstance(manifest.get("items"), list):
        items = manifest["items"]
    else:
        raise ValueError("Manifest must be a list or an object with an items list")

    resolved_items = []
    for item in items:
        resolved_item = dict(item)
        prompt_file = resolved_item.get("prompt_file")
        if prompt_file:
            prompt_path = Path(prompt_file)
            if not prompt_path.is_absolute():
                resolved_item["prompt_file"] = str(
                    (manifest_path.parent / prompt_path).resolve()
                )
        resolved_items.append(resolved_item)
    return resolved_items


def parse_ids(ids_arg):
    if not ids_arg:
        return None
    ids = [item.strip() for item in ids_arg.split(",")]
    return [item for item in ids if item] or None


def select_eval_items(items, ids=None, run_all=False):
    if run_all:
        return list(items)

    requested_ids = ids or []
    if not requested_ids:
        raise EvalSelectionError("Pass --ids ID[,ID...] or --all.")

    items_by_id = {item.get("id"): item for item in items}
    selected = []
    for item_id in requested_ids:
        if item_id not in items_by_id:
            raise EvalSelectionError(f"Unknown eval id: {item_id}")
        selected.append(items_by_id[item_id])
    return selected


def run_cleaner(result_dir, manifest_path):
    import clean_eval_outputs

    result_path = Path(result_dir)
    rows = clean_eval_outputs.clean_all(
        result_path,
        result_path / "clean",
        Path(manifest_path),
    )
    clean_eval_outputs.write_reports(rows, result_path)
    return rows


def run_batch(
    items,
    config,
    result_dir,
    dry_run,
    stop_on_error,
    http_post_json=post_json,
):
    results = []
    for item in items:
        result = run_single_eval(
            item,
            config,
            result_dir,
            dry_run=dry_run,
            http_post_json=http_post_json,
        )
        print(f"{result.eval_id}: {result.status}")
        results.append(result)
        if result.status == "error" and stop_on_error:
            break
    return results


def build_arg_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ids")
    parser.add_argument("--all", action="store_true", dest="run_all")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-clean", action="store_true")
    parser.add_argument("--stop-on-error", action="store_true")
    parser.add_argument("--result-dir", default=str(DEFAULT_RESULT_DIR))
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    return parser


def main(argv=None):
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    result_dir = Path(args.result_dir)
    manifest_path = Path(args.manifest)

    try:
        items = load_manifest_items(manifest_path)
        selected = select_eval_items(items, parse_ids(args.ids), run_all=args.run_all)
        config = load_deepseek_config()
    except (EvalSelectionError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(str(exc))
        return 2

    results = run_batch(
        selected,
        config,
        result_dir,
        dry_run=args.dry_run,
        stop_on_error=args.stop_on_error,
    )

    has_success = any(result.status == "success" for result in results)
    if not args.dry_run and not args.no_clean and has_success:
        run_cleaner(result_dir, manifest_path)

    return 1 if any(result.status == "error" for result in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
