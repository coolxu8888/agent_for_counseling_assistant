import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import run_model_eval
from run_model_eval import (
    EvalSelectionError,
    load_deepseek_config,
    load_env_file,
    load_manifest_items,
    select_eval_items,
)


class RunModelEvalTest(unittest.TestCase):
    def test_load_env_file_reads_key_value_pairs_and_comments(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_path = Path(tmp) / ".env"
            env_path.write_text(
                "\ufeff# comment\nDEEPSEEK_API_KEY=from-file\n\nDEEPSEEK_MODEL=custom\n",
                encoding="utf-8",
            )

            values = load_env_file(env_path)

        self.assertEqual(values["DEEPSEEK_API_KEY"], "from-file")
        self.assertEqual(values["DEEPSEEK_MODEL"], "custom")
        self.assertNotIn("# comment", values)

    def test_load_deepseek_config_defaults_to_v4_flash(self):
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "from-env"}, clear=True):
            config = load_deepseek_config({})

        self.assertEqual(config.api_key, "from-env")
        self.assertEqual(config.model, "deepseek-v4-flash")
        self.assertEqual(config.base_url, "https://api.deepseek.com")
        self.assertEqual(config.timeout_seconds, 120)

    def test_load_deepseek_config_reads_default_env_file_when_no_values_passed(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_path = Path(tmp) / ".env"
            env_path.write_text(
                "DEEPSEEK_API_KEY=from-file\n"
                "DEEPSEEK_MODEL=file-model\n"
                "DEEPSEEK_TIMEOUT_SECONDS=75\n",
                encoding="utf-8",
            )

            with patch.dict(os.environ, {}, clear=True), patch.object(
                run_model_eval, "DEFAULT_ENV_PATH", env_path
            ):
                config = load_deepseek_config()

        self.assertEqual(config.api_key, "from-file")
        self.assertEqual(config.model, "file-model")
        self.assertEqual(config.timeout_seconds, 75)

    def test_load_deepseek_config_honors_timeout_seconds_from_env_values(self):
        with patch.dict(os.environ, {}, clear=True):
            config = load_deepseek_config(
                {"DEEPSEEK_API_KEY": "from-file", "DEEPSEEK_TIMEOUT_SECONDS": "45"}
            )

        self.assertEqual(config.timeout_seconds, 45)

    def test_load_deepseek_config_honors_timeout_seconds_from_process_env(self):
        with patch.dict(
            os.environ,
            {"DEEPSEEK_API_KEY": "from-env", "DEEPSEEK_TIMEOUT_SECONDS": "60"},
            clear=True,
        ):
            config = load_deepseek_config({"DEEPSEEK_TIMEOUT_SECONDS": "45"})

        self.assertEqual(config.timeout_seconds, 60)

    def test_process_env_overrides_env_values(self):
        with patch.dict(
            os.environ,
            {
                "DEEPSEEK_API_KEY": "from-env",
                "DEEPSEEK_MODEL": "model-from-env",
                "DEEPSEEK_BASE_URL": "https://env.example",
            },
            clear=True,
        ):
            config = load_deepseek_config(
                {
                    "DEEPSEEK_API_KEY": "from-file",
                    "DEEPSEEK_MODEL": "model-from-file",
                    "DEEPSEEK_BASE_URL": "https://file.example",
                }
            )

        self.assertEqual(config.api_key, "from-env")
        self.assertEqual(config.model, "model-from-env")
        self.assertEqual(config.base_url, "https://env.example")

    def test_load_deepseek_config_missing_api_key_mentions_name(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ValueError, "DEEPSEEK_API_KEY"):
                load_deepseek_config({})

    def test_select_eval_items_by_ids_preserves_requested_order(self):
        items = [{"id": "W1-001"}, {"id": "W2-001"}, {"id": "W3-001"}]

        selected = select_eval_items(items, ["W3-001", "W1-001"], run_all=False)

        self.assertEqual([item["id"] for item in selected], ["W3-001", "W1-001"])

    def test_select_eval_items_run_all_returns_all_items(self):
        items = [{"id": "W1-001"}, {"id": "W2-001"}]

        selected = select_eval_items(items, ["W1-001"], run_all=True)

        self.assertEqual(selected, items)

    def test_select_eval_items_requires_ids_or_run_all(self):
        items = [{"id": "W1-001"}]

        with self.assertRaisesRegex(EvalSelectionError, "Pass --ids .* or --all"):
            select_eval_items(items)

    def test_select_eval_items_unknown_id_raises_error_mentioning_id(self):
        items = [{"id": "W1-001"}]

        with self.assertRaisesRegex(EvalSelectionError, "W9-999"):
            select_eval_items(items, ["W9-999"], run_all=False)

    def test_load_manifest_items_accepts_object_with_items_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest_path = Path(tmp) / "manifest.json"
            manifest_path.write_text(
                json.dumps({"items": [{"id": "W1-001"}, {"id": "W1-002"}]}),
                encoding="utf-8",
            )

            items = load_manifest_items(manifest_path)

        self.assertEqual([item["id"] for item in items], ["W1-001", "W1-002"])

    def test_load_manifest_items_accepts_list_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest_path = Path(tmp) / "manifest.json"
            manifest_path.write_text(
                json.dumps([{"id": "W1-001"}, {"id": "W1-002"}]),
                encoding="utf-8",
            )

            items = load_manifest_items(manifest_path)

        self.assertEqual([item["id"] for item in items], ["W1-001", "W1-002"])


if __name__ == "__main__":
    unittest.main()
