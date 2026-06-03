import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import run_model_eval
from run_model_eval import (
    DeepSeekConfig,
    EvalSelectionError,
    EvalRunResult,
    build_chat_payload,
    load_deepseek_config,
    load_env_file,
    load_manifest_items,
    parse_ids,
    run_batch,
    run_single_eval,
    select_eval_items,
)


class RunModelEvalTest(unittest.TestCase):
    def test_build_chat_payload_uses_full_prompt_and_defaults(self):
        payload = build_chat_payload("deepseek-test", "第一行\n第二行")

        self.assertEqual(
            payload,
            {
                "model": "deepseek-test",
                "messages": [{"role": "user", "content": "第一行\n第二行"}],
                "temperature": 0.2,
                "max_tokens": 4096,
            },
        )

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

    def test_parse_ids_trims_comma_separated_values_and_skips_empty_items(self):
        self.assertIsNone(parse_ids(None))
        self.assertIsNone(parse_ids(""))
        self.assertEqual(parse_ids(" W1-001, ,W2-001 "), ["W1-001", "W2-001"])

    def test_run_batch_continues_after_error_by_default(self):
        calls = []

        def fake_single(item, config, result_dir, dry_run=False, http_post_json=None):
            calls.append(item["id"])
            status = "error" if item["id"] == "W1-001" else "success"
            return EvalRunResult(item["id"], status, None, Path("meta.json"))

        stdout = io.StringIO()
        with patch.object(
            run_model_eval, "run_single_eval", fake_single
        ), contextlib.redirect_stdout(stdout):
            results = run_batch(
                [{"id": "W1-001"}, {"id": "W1-002"}],
                DeepSeekConfig(api_key="key"),
                Path("results"),
                dry_run=False,
                stop_on_error=False,
                http_post_json=lambda *_args: None,
            )

        self.assertEqual(calls, ["W1-001", "W1-002"])
        self.assertEqual([result.status for result in results], ["error", "success"])

    def test_run_batch_stops_after_error_when_requested(self):
        calls = []

        def fake_single(item, config, result_dir, dry_run=False, http_post_json=None):
            calls.append(item["id"])
            return EvalRunResult(item["id"], "error", None, Path("meta.json"))

        stdout = io.StringIO()
        with patch.object(
            run_model_eval, "run_single_eval", fake_single
        ), contextlib.redirect_stdout(stdout):
            results = run_batch(
                [{"id": "W1-001"}, {"id": "W1-002"}],
                DeepSeekConfig(api_key="key"),
                Path("results"),
                dry_run=False,
                stop_on_error=True,
                http_post_json=lambda *_args: None,
            )

        self.assertEqual(calls, ["W1-001"])
        self.assertEqual([result.eval_id for result in results], ["W1-001"])

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

    def test_run_single_eval_dry_run_writes_only_metadata_and_never_calls_http(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            prompt_path = tmp_path / "missing-prompt.txt"
            result_dir = tmp_path / "results"
            config = DeepSeekConfig(
                api_key="secret-key", model="deepseek-test", base_url="https://api.test"
            )

            def fail_http(*_args, **_kwargs):
                raise AssertionError("HTTP should not be called during dry run")

            result = run_single_eval(
                {"id": "W1-001", "prompt_file": str(prompt_path)},
                config,
                result_dir,
                dry_run=True,
                http_post_json=fail_http,
            )

            meta_path = result_dir / "W1-001-deepseek-api-meta.json"
            raw_path = result_dir / "W1-001-deepseek-api-raw.txt"
            meta = json.loads(meta_path.read_text(encoding="utf-8"))

        self.assertEqual(result.status, "dry_run")
        self.assertIsNone(result.raw_path)
        self.assertFalse(raw_path.exists())
        self.assertEqual(meta["status"], "dry_run")
        self.assertEqual(meta["model"], "deepseek-test")
        self.assertEqual(meta["provider"], "deepseek")
        self.assertTrue(meta["has_api_key"])
        self.assertEqual(meta["planned_raw_file"], str(raw_path))
        self.assertNotIn("secret-key", json.dumps(meta, ensure_ascii=False))

    def test_run_single_eval_success_writes_raw_answer_and_metadata(self):
        calls = []

        def fake_http(url, headers, payload, timeout):
            calls.append(
                {"url": url, "headers": headers, "payload": payload, "timeout": timeout}
            )
            return {
                "choices": [
                    {
                        "message": {"content": "评估完成"},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"total_tokens": 12},
            }

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            prompt_path = tmp_path / "prompt.txt"
            prompt_path.write_text("完整提示\n包含换行", encoding="utf-8")
            result_dir = tmp_path / "results"
            config = DeepSeekConfig(
                api_key="secret-key",
                model="deepseek-test",
                base_url="https://api.test/",
                timeout_seconds=7,
            )

            result = run_single_eval(
                {"id": "W1-002", "prompt_file": str(prompt_path)},
                config,
                result_dir,
                http_post_json=fake_http,
            )

            raw_path = result_dir / "W1-002-deepseek-api-raw.txt"
            meta_path = result_dir / "W1-002-deepseek-api-meta.json"
            raw_text = raw_path.read_text(encoding="utf-8")
            meta_text = meta_path.read_text(encoding="utf-8")
            meta = json.loads(meta_text)

        self.assertEqual(result.status, "success")
        self.assertEqual(result.raw_path, raw_path)
        self.assertEqual(raw_text, "评估完成\n")
        self.assertEqual(calls[0]["url"], "https://api.test/chat/completions")
        self.assertEqual(calls[0]["headers"]["Authorization"], "Bearer secret-key")
        self.assertEqual(
            calls[0]["payload"]["messages"][0]["content"], "完整提示\n包含换行"
        )
        self.assertEqual(calls[0]["timeout"], 7)
        self.assertEqual(meta["status"], "success")
        self.assertEqual(meta["raw_file"], str(raw_path))
        self.assertEqual(meta["model"], "deepseek-test")
        self.assertEqual(meta["base_url"], "https://api.test/")
        self.assertEqual(meta["provider"], "deepseek")
        self.assertTrue(meta["has_api_key"])
        self.assertIn("created_at", meta)
        self.assertIsInstance(meta["latency_seconds"], float)
        self.assertEqual(meta["usage"], {"total_tokens": 12})
        self.assertEqual(meta["finish_reason"], "stop")
        self.assertNotIn("secret-key", meta_text)

    def test_run_single_eval_api_error_writes_error_metadata_and_no_raw_file(self):
        def fake_http(*_args, **_kwargs):
            raise RuntimeError("HTTP 401: secret-key unauthorized")

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            prompt_path = tmp_path / "prompt.txt"
            prompt_path.write_text("prompt", encoding="utf-8")
            result_dir = tmp_path / "results"
            config = DeepSeekConfig(api_key="secret-key")

            result = run_single_eval(
                {"id": "W1-003", "prompt_file": str(prompt_path)},
                config,
                result_dir,
                http_post_json=fake_http,
            )

            raw_path = result_dir / "W1-003-deepseek-api-raw.txt"
            meta_text = (result_dir / "W1-003-deepseek-api-meta.json").read_text(
                encoding="utf-8"
            )
            meta = json.loads(meta_text)

        self.assertEqual(result.status, "error")
        self.assertIsNone(result.raw_path)
        self.assertFalse(raw_path.exists())
        self.assertEqual(meta["error_type"], "api_error")
        self.assertNotIn("secret-key", meta_text)

    def test_run_single_eval_malformed_response_writes_error_metadata_and_no_raw_file(self):
        def fake_http(*_args, **_kwargs):
            return {"choices": [{"message": {}}]}

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            prompt_path = tmp_path / "prompt.txt"
            prompt_path.write_text("prompt", encoding="utf-8")
            result_dir = tmp_path / "results"
            config = DeepSeekConfig(api_key="secret-key")

            result = run_single_eval(
                {"id": "W1-004", "prompt_file": str(prompt_path)},
                config,
                result_dir,
                http_post_json=fake_http,
            )

            raw_path = result_dir / "W1-004-deepseek-api-raw.txt"
            meta_text = (result_dir / "W1-004-deepseek-api-meta.json").read_text(
                encoding="utf-8"
            )
            meta = json.loads(meta_text)

        self.assertEqual(result.status, "error")
        self.assertIsNone(result.raw_path)
        self.assertFalse(raw_path.exists())
        self.assertEqual(meta["error_type"], "malformed_response")
        self.assertNotIn("secret-key", meta_text)


if __name__ == "__main__":
    unittest.main()
