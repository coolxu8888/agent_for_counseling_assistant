# DeepSeek Template Mapper Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an optional DeepSeek-assisted mapper that maps unresolved Word template slots to allowed `structured_output.json` source paths, while keeping final DOCX filling deterministic.

**Architecture:** Extend `scripts/fill_docx_template.py` with a constrained LLM mapping layer. The script first builds deterministic `template_mapping.json`; if `--llm-map` is enabled, it sends only unresolved slots and allowed source paths to DeepSeek, validates the returned JSON, merges accepted mappings back into the mapping, and then fills the document from the validated mapping.

**Tech Stack:** Python standard library plus existing project DeepSeek helpers from `scripts/run_model_eval.py` (`load_deepseek_config`, `build_chat_payload`, `deepseek_chat_completions_url`, `post_json`, `extract_answer_text`), PowerShell wrapper, `unittest`.

---

## File Structure

- Modify: `scripts/fill_docx_template.py`
  - Add prompt generation, LLM response extraction/validation, optional DeepSeek mapping call, and CLI options.
- Modify: `scripts/test_fill_docx_template.py`
  - Add tests for prompt construction, validation, merge behavior, and mocked DeepSeek call.
- Modify: `scripts/fill-docx-template.ps1`
  - Add `-LlmMap`.
- Modify: `README.md`
  - Document the optional DeepSeek mapping workflow.

---

## Task 1: Prompt and Response Validation

**Files:**
- Modify: `scripts/test_fill_docx_template.py`
- Modify: `scripts/fill_docx_template.py`

- [ ] **Step 1: Add failing tests**

Add tests for:

```python
prompt = build_llm_mapping_prompt(unmapped_slots, source_paths)
self.assertIn("JSON only", prompt)
self.assertIn("source_path", prompt)
self.assertIn("unmapped", prompt)
```

Add tests for parsing fenced JSON:

```python
response = "```json\n{\"mappings\":[...]}\n```"
mapping = extract_llm_mapping_json(response)
```

Add validation tests:

- valid `source_path` with `confidence: "medium"` becomes `fill_status: "ready"`.
- unknown `source_path` becomes `source_path: "unmapped"`, `confidence: "none"`, `fill_status: "skipped"`.
- `confidence: "low"` remains skipped.

- [ ] **Step 2: Run test to verify failure**

Run:

```powershell
$env:PYTHONPATH='scripts'; python -m unittest scripts.test_fill_docx_template
```

- [ ] **Step 3: Implement prompt and validation helpers**

Implement:

```python
def unresolved_mapping_items(mapping): ...
def build_llm_mapping_prompt(slots, source_paths): ...
def extract_llm_mapping_json(answer_text): ...
def validate_llm_mapping(mapping, requested_slot_ids, allowed_source_paths): ...
def merge_template_mappings(base_mapping, llm_mapping): ...
```

Rules:

- LLM can only return source paths from `allowed_source_paths` or `unmapped`.
- `high` and `medium` may become `fill_status: "ready"`.
- `low`, `none`, unknown source paths, and malformed items become `fill_status: "skipped"`.
- unknown slot IDs are ignored.

- [ ] **Step 4: Run test to verify pass**

Run:

```powershell
$env:PYTHONPATH='scripts'; python -m unittest scripts.test_fill_docx_template
```

- [ ] **Step 5: Commit**

Run:

```powershell
git add scripts/fill_docx_template.py scripts/test_fill_docx_template.py
git commit -m "Validate LLM template mappings"
```

---

## Task 2: DeepSeek Mapping Call

**Files:**
- Modify: `scripts/test_fill_docx_template.py`
- Modify: `scripts/fill_docx_template.py`

- [ ] **Step 1: Add failing mocked API tests**

Add a test with fake `http_post_json`:

```python
def fake_post(url, headers, payload, timeout):
    return {"choices": [{"message": {"content": "{\"mappings\": [...]}"}}]}
```

Assert:

- `run_deepseek_template_mapping(...)` calls the fake post only for unresolved slots.
- returned mapping merges LLM result into deterministic mapping.
- if all slots are already ready, API is not called.

- [ ] **Step 2: Run test to verify failure**

Run:

```powershell
$env:PYTHONPATH='scripts'; python -m unittest scripts.test_fill_docx_template
```

- [ ] **Step 3: Implement DeepSeek mapping function**

Implement:

```python
def run_deepseek_template_mapping(base_mapping, source_paths, config, http_post_json=post_json): ...
```

Use existing helpers:

- `build_chat_payload`
- `deepseek_chat_completions_url`
- `extract_answer_text`
- `post_json`

Do not log API keys. Return:

```json
{
  "mapping": {...},
  "llm_status": "success|skipped|error",
  "llm_issues": []
}
```

- [ ] **Step 4: Run test to verify pass**

Run:

```powershell
$env:PYTHONPATH='scripts'; python -m unittest scripts.test_fill_docx_template
```

- [ ] **Step 5: Commit**

Run:

```powershell
git add scripts/fill_docx_template.py scripts/test_fill_docx_template.py
git commit -m "Map DOCX template slots with DeepSeek"
```

---

## Task 3: CLI and Wrapper

**Files:**
- Modify: `scripts/test_fill_docx_template.py`
- Modify: `scripts/fill_docx_template.py`
- Modify: `scripts/fill-docx-template.ps1`
- Modify: `README.md`

- [ ] **Step 1: Add failing CLI tests**

Add tests for:

```text
--llm-map
```

Add `main()` test using a fake mapper injection if needed, or test argument parsing plus `write_mapping_artifacts(..., llm_map=False)` separately.

- [ ] **Step 2: Run test to verify failure**

Run:

```powershell
$env:PYTHONPATH='scripts'; python -m unittest scripts.test_fill_docx_template
```

- [ ] **Step 3: Implement CLI option**

Add:

```text
--llm-map
```

Behavior:

- generate deterministic mapping first;
- when `--llm-map` is set and `--mapping-input` is absent, call DeepSeek for unresolved mappings;
- write final mapping to `--mapping-output` when provided;
- fill DOCX from the final mapping.

- [ ] **Step 4: Extend PowerShell wrapper**

Add:

```powershell
[switch]$LlmMap
```

Pass `--llm-map` when set.

- [ ] **Step 5: Update README**

Document:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\fill-docx-template.ps1 -TemplatePath path\template.docx -StructuredPath agent-runs\<run>\structured_output.json -OutputPath path\filled_template.docx -MappingOutput path\template_mapping.json -LlmMap
```

Explain that the model only maps unresolved slots to allowed source paths.

- [ ] **Step 6: Run full tests**

Run:

```powershell
$env:PYTHONPATH='scripts'; python -m unittest discover -s scripts -p "test_*.py"
```

- [ ] **Step 7: Commit**

Run:

```powershell
git add scripts/fill_docx_template.py scripts/test_fill_docx_template.py scripts/fill-docx-template.ps1 README.md
git commit -m "Expose DeepSeek template mapping option"
```

---

## Final Verification

Run:

```powershell
git status --short
$env:PYTHONPATH='scripts'; python -m unittest discover -s scripts -p "test_*.py"
```

Optional real smoke test after tests pass:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\fill-docx-template.ps1 -TemplatePath path\template.docx -StructuredPath agent-runs\<run>\structured_output.json -OutputPath path\filled_template.docx -MappingOutput path\template_mapping.json -LlmMap
```

Expected:

- Unit tests pass.
- Mapping output remains valid JSON.
- Final DOCX fill still uses code, not free-form model output.
