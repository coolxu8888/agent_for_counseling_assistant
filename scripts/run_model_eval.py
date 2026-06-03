import json
import os
from dataclasses import dataclass
from pathlib import Path


DEFAULT_DEEPSEEK_MODEL = "deepseek-v4-flash"
DEFAULT_DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEFAULT_DEEPSEEK_TIMEOUT = 120
ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ENV_PATH = ROOT / ".env"


class EvalSelectionError(ValueError):
    pass


@dataclass(frozen=True)
class DeepSeekConfig:
    api_key: str
    model: str = DEFAULT_DEEPSEEK_MODEL
    base_url: str = DEFAULT_DEEPSEEK_BASE_URL
    timeout_seconds: int = DEFAULT_DEEPSEEK_TIMEOUT


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
        return manifest
    if isinstance(manifest, dict) and isinstance(manifest.get("items"), list):
        return manifest["items"]
    raise ValueError("Manifest must be a list or an object with an items list")


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
