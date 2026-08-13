# Market Validation Documentation Freeze Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Freeze the product stage as “市场验证版” and reduce repository Markdown to Web operations plus prompts and RAG chunks read at runtime.

**Architecture:** Derive a Markdown whitelist from code. Keep `README.md`, the hard-coded system prompt, and RAG files with a non-empty `chunk_id`; merge deployment commands into README and remove all other tracked Markdown except dirty user-owned files.

**Tech Stack:** Markdown, PowerShell, Python unittest, Git, Render Blueprint.

---

### Task 1: Derive the runtime whitelist

**Files:**
- Inspect: `scripts/run_agent.py`
- Inspect: `scripts/build_workflow_eval_prompts.py`
- Inspect: all tracked `*.md`

- [ ] **Step 1: List tracked Markdown and dirty paths**

Run `git ls-files '*.md'` and `git status --short`.

Expected: all tracked Markdown is visible and pre-existing changes remain identifiable.

- [ ] **Step 2: Generate the keep set**

Keep exactly `README.md`, `counselor-agent-v0.1-system-prompt.md`, and `rag/**/*.md` files containing a non-empty line matching `^chunk_id:\s*\S+`.

Expected: indexes, source cards, rejected sources, templates, reviews, and reports are excluded because `_index_rag_chunks()` does not load them into model context.

- [ ] **Step 3: Protect dirty user work**

Run `git diff --name-only`.

Expected: no pre-existing dirty path is deleted or rewritten. A dirty Markdown outside the keep set is reported as a temporary exception.

### Task 2: Replace README with the operational entry point

**Files:**
- Modify: `README.md`
- Inspect then delete: `docs/coze-render-deployment.md`

- [ ] **Step 1: Write the README contract**

Write only: the title `咨询师助理 Agent｜市场验证版`; compatibility explanation for `v0.1` and `0.1.0`; de-identification warning; local command `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run-web-workbench.ps1`; default URL; exact Render command `python scripts/web_workbench.py --host 0.0.0.0 --port $PORT`; required/optional environment variables; system-prompt and RAG-prompt inventory.

- [ ] **Step 2: Verify command parity**

Run `rg -n 'run-web-workbench|web_workbench.py --host 0.0.0.0 --port \$PORT' README.md render.yaml`.

Expected: README contains the local command and exact Render start command.

### Task 3: Remove non-runtime Markdown

**Files:**
- Delete: every tracked Markdown path outside the keep set, except pre-existing dirty paths

- [ ] **Step 1: Delete the code-derived removal set**

Use `apply_patch` for the enumerated tracked files. Include historical root documents, eval documentation/results, `docs/superpowers/**`, deployment notes merged into README, and non-chunk RAG maintenance files.

Expected: no file containing a non-empty `chunk_id` is deleted.

- [ ] **Step 2: Confirm runtime references**

Run `rg -n '\.md' scripts web-workbench render.yaml -g '*.py' -g '*.ps1' -g '*.js' -g '*.html' -g '*.yaml'`.

Expected: the system prompt exists; generated `clean_output.md` references remain valid; eval-only references do not affect Web runtime.

### Task 4: Validate frozen scope

**Files:**
- Verify: all remaining tracked Markdown
- Test: `scripts/test_run_agent.py`
- Test: `scripts/test_web_workbench.py`

- [ ] **Step 1: Audit remaining Markdown**

Run a PowerShell whitelist check that fails when a tracked Markdown is neither README, the system prompt, a RAG file with non-empty `chunk_id`, nor the protected dirty exception.

Expected: PASS with the exact exception list printed.

- [ ] **Step 2: Audit product-stage wording**

Run `rg -n -i '市场验证版|Market Validation|MVP|v0\.2|v0\.1' README.md counselor-agent-v0.1-system-prompt.md rag -g '*.md'`.

Expected: README names only “市场验证版”; residual `v0.1` is marked as compatibility language or rewritten without changing prompt behavior; no `v0.2` roadmap remains.

- [ ] **Step 3: Run runtime tests**

Run `$env:PYTHONPATH='scripts'; python -m unittest scripts.test_run_agent scripts.test_web_workbench -v`.

Expected: all tests pass.

- [ ] **Step 4: Review the final diff**

Run `git diff --check`, `git status --short`, and `git diff --stat`.

Expected: no whitespace errors; pre-existing code changes remain intact; only README and intended Markdown deletions are added by this task.
