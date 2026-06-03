# DeepSeek API Eval Runner Design

Date: 2026-06-03

## Goal

Build a DeepSeek API runner for the existing counselor-agent eval pipeline.

The runner replaces the fragile DeepSeek Web automation path for routine eval work. It should read the existing workflow eval prompts, call DeepSeek `deepseek-v4-flash`, save raw outputs and metadata, then automatically trigger the existing clean/rubric summary pipeline.

This is an eval automation layer, not the final product backend.

## Scope

In scope:

- Run selected eval prompts from `eval-prompts/manifest.json`.
- Use DeepSeek Chat Completions with default model `deepseek-v4-flash`.
- Read API configuration from local environment variables or a local `.env` file.
- Save raw model responses under `eval-results/api/`.
- Save per-run metadata without storing the API key.
- Automatically run the existing output cleaning and rubric scoring step after successful model calls.
- Support dry-run mode so prompt selection can be checked without spending API credits.
- Add tests with a fake HTTP client or mocked transport; tests must not call the real DeepSeek API.

Out of scope:

- Building the user-facing backend service.
- Connecting a frontend.
- Streaming UI output.
- Multi-turn chat memory.
- Real clinical risk triage automation.
- Final risk level judgment for real cases.
- Full provider abstraction across many vendors.

## Configuration

The first version should be DeepSeek-specific, with names that are easy to understand:

```text
DEEPSEEK_API_KEY=
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-v4-flash
DEEPSEEK_TIMEOUT_SECONDS=120
```

`DEEPSEEK_MODEL` defaults to `deepseek-v4-flash` if omitted.

The repository should include `.env.example`, but not `.env`.

The runner must never print or write the API key. Metadata can record whether a key was present, the model name, base URL host, request timestamp, latency, status, token usage if returned, and error category if any.

## Command Interface

PowerShell wrapper:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run-model-eval.ps1 -Ids W1-001,W3-001
```

Python entry point:

```powershell
python scripts\run_model_eval.py --ids W1-001,W3-001
```

Recommended options:

```text
--ids W1-001,W3-001       Run only selected eval ids.
--all                     Run every item in manifest.
--dry-run                 Validate prompt selection and output paths without calling DeepSeek.
--no-clean                Save raw outputs only; skip clean/rubric step.
--stop-on-error           Stop the batch after the first failed API call.
--result-dir PATH         Default: eval-results/api
--manifest PATH           Default: eval-prompts/manifest.json
```

The wrapper should default to auto-clean after calls complete.

## Data Flow

```text
eval-prompts/manifest.json
  -> select eval ids
  -> read prompt_file
  -> build DeepSeek chat completion request
  -> call DeepSeek API
  -> save raw answer and metadata
  -> run clean_eval_outputs.py against eval-results/api
  -> write clean outputs and rubric summaries
```

The request should send the full eval prompt as a user message. The existing prompt files already contain the system prompt, workflow constraints, RAG context, user input, and expected eval marker. Keeping the request simple avoids maintaining two parallel prompt assembly systems.

## Output Files

For each eval id:

```text
eval-results/api/<EVAL_ID>-deepseek-api-raw.txt
eval-results/api/<EVAL_ID>-deepseek-api-meta.json
```

Clean outputs should be placed under:

```text
eval-results/api/clean/<EVAL_ID>-clean.md
```

API eval summaries should remain separate from the old Web eval summaries:

```text
eval-results/api/eval-clean-summary.v0.1.md
eval-results/api/eval-clean-summary.v0.1.json
eval-results/api/eval-rubric-summary.v0.1.md
eval-results/api/eval-rubric-summary.v0.1.json
```

This preserves the old `eval-results/*-deepseek-raw.txt` files as historical Web results.

## DeepSeek Request Shape

The runner should call DeepSeek Chat Completions using the documented API shape:

```json
{
  "model": "deepseek-v4-flash",
  "messages": [
    {
      "role": "user",
      "content": "<full eval prompt file>"
    }
  ],
  "temperature": 0.2,
  "max_tokens": 4096
}
```

Default temperature should be low for eval reproducibility. A future version can expose model parameters in a config file.

Official reference checked on 2026-06-03: https://api-docs.deepseek.com/api/create-chat-completion

## Error Handling

Key missing:

- Exit with a clear message telling the user to create `.env` from `.env.example`.
- Do not create raw output files.

Single eval API failure:

- Write a metadata file with `status: "error"`, `error_type`, and a short sanitized error message.
- Do not write a fake raw answer.
- Continue to the next eval by default.

Timeout or rate limit:

- Record the error category.
- Continue by default unless `--stop-on-error` is set.

Malformed API response:

- Record `status: "error"` and `error_type: "malformed_response"`.
- Do not pass that eval to the cleaner.

Cleaner integration:

- The existing cleaner should be extended to discover both `*-deepseek-raw.txt` and `*-deepseek-api-raw.txt`, or accept a raw filename pattern.
- API outputs should be cleaned into `eval-results/api/clean/` so they do not overwrite Web eval clean files.

## Testing

Tests should cover:

- Eval id selection from manifest.
- Dry-run does not call API and reports planned output paths.
- Request payload contains the selected model and full prompt text.
- Successful fake response writes raw output and metadata.
- Failed fake response writes error metadata and no raw answer.
- Missing API key fails early without leaking secrets.
- Cleaner can process API raw filenames.

No automated test should call the real DeepSeek API.

## Acceptance Criteria

The design is implemented when:

- `.env.example` documents required DeepSeek settings.
- `scripts/run_model_eval.py` and `scripts/run-model-eval.ps1` exist.
- `deepseek-v4-flash` is the default model.
- Running selected eval ids saves raw API outputs and metadata under `eval-results/api/`.
- The command automatically produces clean outputs and rubric summaries under `eval-results/api/`.
- Existing DeepSeek Web eval files and summaries remain untouched by default.
- Tests pass locally without a real API key.
- RAG validation and existing eval cleaner tests still pass.
