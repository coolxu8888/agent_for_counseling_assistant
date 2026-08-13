# Single Web Service Consolidation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the retired Coze compatibility channel without losing current Web, mobile API, iOS, evaluation, or document-generation work, and make `https://counselor-agent-web.onrender.com` the only deployed product service.

**Architecture:** `scripts/web_workbench.py` remains the single HTTP service for browser assets, Web session APIs, `/api/mobile/v1`, authenticated downloads, health checks, Agent routing, RAG, validation, and document generation. The compatibility wrapper and its schemas are deleted only after the standalone service contracts are locked by tests. Current uncommitted work is first checkpointed, then merged with the latest remote `main` in an isolated linked worktree.

**Tech Stack:** Python 3 standard library HTTP server and `unittest`, vanilla HTML/CSS/JavaScript, PowerShell, Swift/Xcode configuration files, Render Blueprint YAML, Git linked worktrees.

## Global Constraints

- The only product URL is `https://counselor-agent-web.onrender.com`.
- Preserve all current non-Coze tracked and untracked work, including iOS, mobile API, evaluation fixes, product documents, and Web changes.
- Never run `git reset --hard`, `git clean -fdx`, or delete any existing `.worktrees/` entry.
- The final current worktree, excluding `.git/` and other linked worktrees, must contain no case-insensitive `coze`, `counselor-agent-coze-api`, or `COZE_DEMO_API_KEY` match.
- Git commit history is not rewritten. The transitional design and this implementation plan are deleted in the final repository-cleanup commit.
- Do not migrate the frontend to React/Next.js and do not refactor unrelated Agent, RAG, evaluation, or document-generation code.
- Remote service deletion and secret transmission require a browser action-time confirmation even though repository cleanup is already approved.
- Run Tasks 2-8 from the linked `.worktrees/single-web-service` worktree unless a step explicitly says to return to the original repository root.

---

### Task 1: Preserve Current Work and Create the Isolated Integration Worktree

**Files:**
- Modify: `.gitignore`
- Preserve unchanged: every currently modified or untracked non-temporary file
- Ignore/remove later: `.superpowers/brainstorm/`

**Interfaces:**
- Consumes: current `main` at design commit `d155de1` plus all tracked/untracked user work
- Produces: recovery branch `codex/pre-single-web-snapshot` and implementation branch/worktree `codex/single-web-service` at `.worktrees/single-web-service`

- [ ] **Step 1: Invoke the required worktree safety skill and verify the starting state**

Read and follow `superpowers:using-git-worktrees`, then run:

```powershell
git status --short --branch
git worktree list --porcelain
git branch --list codex/pre-single-web-snapshot codex/single-web-service
```

Expected: current branch is `main`; staged area is empty; the two new branch names do not exist; existing linked worktrees remain untouched.

- [ ] **Step 2: Ignore tool-only brainstorming state**

Use `apply_patch` to add this exact block to `.gitignore`:

```gitignore

# Local Superpowers brainstorming previews and process state.
.superpowers/
```

Run:

```powershell
git status --short --ignored .superpowers
```

Expected: `.superpowers/` is reported as ignored, not staged.

- [ ] **Step 3: Create a recoverable checkpoint branch and commit all non-temporary work**

```powershell
git switch -c codex/pre-single-web-snapshot
git add -A
git diff --cached --check
git diff --cached --name-only
```

Before committing, verify the staged list contains no `.env`, `.superpowers/`, `agent-runs/`, `workbench-data/`, or `workbench-run-log.jsonl`. Then run:

```powershell
git commit -m "chore: preserve current product work"
git status --short
```

Expected: the original working directory is clean and all current product work is recoverable from `codex/pre-single-web-snapshot`.

- [ ] **Step 4: Fetch the latest remote main and create the linked implementation worktree**

```powershell
git fetch origin main
git worktree add '.worktrees/single-web-service' -b codex/single-web-service codex/pre-single-web-snapshot
git -C '.worktrees/single-web-service' merge --no-ff origin/main -m "Merge latest main before single-service consolidation"
```

If Git reports conflicts, resolve each file by preserving the semantic union of remote changes and checkpointed Web/mobile/iOS work. Do not restore any already-retired feature merely to avoid a conflict. Finish with:

```powershell
git -C '.worktrees/single-web-service' diff --check
git -C '.worktrees/single-web-service' status --short
```

Expected: merge completes and the linked worktree is clean.

- [ ] **Step 5: Establish a passing baseline in the linked worktree**

```powershell
$integrationRoot = (Resolve-Path '.worktrees/single-web-service').Path
Push-Location $integrationRoot
try {
    $env:PYTHONPATH = Join-Path $integrationRoot 'scripts'
    python -m unittest scripts.test_clean_eval_outputs scripts.test_web_workbench scripts.test_mobile_api_contract scripts.test_hosted_smoke
    node --check web-workbench/app.js
} finally {
    Pop-Location
}
```

Expected: all selected tests pass and JavaScript syntax is valid.

---

### Task 2: Make Hosted Smoke Testing Depend Only on the Product Service

**Files:**
- Modify: `scripts/hosted_smoke.py:107-145`
- Modify: `scripts/test_hosted_smoke.py:40-242`

**Interfaces:**
- Consumes: `request_json(base_url, path, ...)` and `/health`, `/api/session`, `/api/login`, `/api/signup`, `/api/run`
- Produces: `run_smoke(...) -> dict` with `deployment_readiness`, authentication mode, and optional workflow evidence without compatibility metadata endpoints

- [ ] **Step 1: Write the failing product-endpoint sequence test**

Add this test to `HostedSmokeTest`:

```python
def test_run_smoke_uses_only_product_endpoints(self):
    request_json = Mock(
        side_effect=[
            (200, {"status": "ok"}, {}),
            (
                200,
                {
                    "auth_config": {"signup_enabled": False, "invite_required": False},
                    "deployment_readiness": {
                        "pilot_ready": True,
                        "summary": {"fail_count": 0, "warn_count": 0},
                        "checks": [],
                    },
                },
                {},
            ),
            (200, {"status": "success", "user": {"username": "pilot"}}, {"set-cookie": "session=abc"}),
        ]
    )

    hosted_smoke.run_smoke(
        "https://example.test",
        username="pilot",
        password="pilot-pass-123",
        skip_run=True,
        request_json=request_json,
    )

    self.assertEqual(
        [call.args[1] for call in request_json.call_args_list],
        ["/health", "/api/session", "/api/login"],
    )
```

- [ ] **Step 2: Run the new test and verify the old sequence fails**

```powershell
python -m unittest scripts.test_hosted_smoke.HostedSmokeTest.test_run_smoke_uses_only_product_endpoints
```

Expected: FAIL because the current smoke runner also requests `/service-info` and `/openapi.json`.

- [ ] **Step 3: Replace metadata checks with one unconditional session/readiness check**

In `run_smoke`, keep the health step and replace the old metadata blocks plus the nested session block with this structure:

```python
def session_step():
    status, payload, _headers = request_json(report["base_url"], "/api/session", timeout=timeout)
    _require(status == 200, f"/api/session returned HTTP {status}.")
    readiness = payload.get("deployment_readiness")
    if readiness:
        _validate_readiness(readiness, expect_pilot_ready)
        report["deployment_readiness"] = readiness
    return payload

session_payload = _run_step(report, "session", session_step)
auth_config = session_payload.get("auth_config") or {}

auth_headers = {}
if not skip_auth:
    # Preserve the existing signup/login selection and cookie handling here.
```

Delete the two compatibility metadata step functions and calls. Keep all existing authentication, route assertions, and real workflow behavior unchanged.

- [ ] **Step 4: Update every hosted-smoke fixture to the new request order**

For each `side_effect` list in `scripts/test_hosted_smoke.py`:

- keep health as response 1;
- keep `/api/session` readiness/auth data as response 2;
- delete metadata and schema responses;
- make login/signup response 3 when authentication is enabled;
- make `/api/run` response 4 when a run is enabled;
- update call indexes accordingly (`/api/login` or `/api/signup` at index 2, `/api/run` at index 3).

For `test_run_smoke_rejects_not_ready_deployment_when_required`, use only health plus a failing `/api/session` readiness response so the test still works with `skip_auth=True`.

- [ ] **Step 5: Run hosted-smoke tests**

```powershell
python -m unittest scripts.test_hosted_smoke
```

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add scripts/hosted_smoke.py scripts/test_hosted_smoke.py
git commit -m "test: focus hosted smoke on product endpoints"
```

---

### Task 3: Lock the Single-Service Deployment and iOS Host Contract

**Files:**
- Create: `scripts/test_deployment_contract.py`
- Modify: `render.yaml`
- Modify: `.env.example`
- Modify: `ios-app/Config/Debug.xcconfig`
- Modify: `ios-app/Config/Release.xcconfig`

**Interfaces:**
- Consumes: Render Blueprint text and iOS build configurations
- Produces: exactly one Render service named `counselor-agent-web`, launched by `scripts/web_workbench.py`, and both iOS variants using the same HTTPS host

- [ ] **Step 1: Write the failing deployment contract tests**

Create `scripts/test_deployment_contract.py`:

```python
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_XCCONFIG = "COUNSELOR_API_BASE_URL = https:/$()/counselor-agent-web.onrender.com/"


class DeploymentContractTest(unittest.TestCase):
    def test_render_blueprint_declares_only_the_web_product(self):
        blueprint = (ROOT / "render.yaml").read_text(encoding="utf-8")
        self.assertEqual(blueprint.count("  - type: web"), 1)
        self.assertIn("name: counselor-agent-web", blueprint)
        self.assertIn(
            "startCommand: python scripts/web_workbench.py --host 0.0.0.0 --port $PORT",
            blueprint,
        )

    def test_ios_build_variants_use_the_web_product_host(self):
        for relative in ("ios-app/Config/Debug.xcconfig", "ios-app/Config/Release.xcconfig"):
            content = (ROOT / relative).read_text(encoding="utf-8")
            self.assertIn(EXPECTED_XCCONFIG, content)

    def test_environment_example_keeps_required_product_configuration(self):
        example = (ROOT / ".env.example").read_text(encoding="utf-8")
        for name in (
            "DEEPSEEK_API_KEY=",
            "DEEPSEEK_BASE_URL=",
            "DEEPSEEK_MODEL=",
            "WORKBENCH_USER=",
            "WORKBENCH_PASSWORD=",
        ):
            self.assertIn(name, example)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the deployment tests and verify they fail**

```powershell
python -m unittest scripts.test_deployment_contract
```

Expected: FAIL because the Blueprint currently declares two Web services and iOS points to the retired host.

- [ ] **Step 3: Reduce the Render Blueprint to the standalone Web service**

Use `apply_patch` to remove the entire second service block from `render.yaml`. Keep the first block unchanged, including:

```yaml
services:
  - type: web
    name: counselor-agent-web
    runtime: python
    plan: free
    buildCommand: pip install -r requirements.txt
    startCommand: python scripts/web_workbench.py --host 0.0.0.0 --port $PORT
    healthCheckPath: /health
```

Keep its DeepSeek, workbench authentication, upload, and 14-day retention variables.

- [ ] **Step 4: Remove the retired shared-secret block from `.env.example`**

Use `apply_patch` to delete the three-comment/variable block between `DEEPSEEK_TIMEOUT_SECONDS=120` and `# Local/web workbench login.`. Keep all product configuration entries.

- [ ] **Step 5: Point both iOS variants to the standalone host**

Set line 3 in both xcconfig files to exactly:

```xcconfig
COUNSELOR_API_BASE_URL = https:/$()/counselor-agent-web.onrender.com/
```

- [ ] **Step 6: Run tests and commit**

```powershell
python -m unittest scripts.test_deployment_contract scripts.test_mobile_api_contract
git add render.yaml .env.example ios-app/Config/Debug.xcconfig ios-app/Config/Release.xcconfig scripts/test_deployment_contract.py
git commit -m "chore: unify deployment on the standalone web service"
```

Expected: PASS, then a focused deployment-contract commit.

---

### Task 4: Prove Standalone Web/Mobile Coverage and Delete the Adapter

**Files:**
- Verify/modify only if coverage is missing: `scripts/test_web_workbench.py`
- Verify/modify only if coverage is missing: `scripts/test_mobile_api_contract.py`
- Delete: `scripts/coze_api_server.py`
- Delete: `scripts/run-coze-api.ps1`
- Delete: `scripts/test_coze_api_server.py`
- Delete: `docs/coze-demo-integration-plan.md`
- Delete: `docs/coze-render-deployment.md`
- Delete: `docs/coze-openapi.json`
- Delete: `docs/coze-openapi.coze-min.json`
- Delete: `docs/coze-openapi.swagger2.json`

**Interfaces:**
- Consumes: `web_workbench.create_server(host, port)`, `WorkbenchHandler`, Web cookie authentication, mobile Bearer authentication, case/run/template/download handlers
- Produces: the same standalone Web/mobile behavior with no wrapper module or schema assets

- [ ] **Step 1: Run the existing standalone characterization coverage before deletion**

```powershell
python -m unittest `
  scripts.test_web_workbench.WebWorkbenchTest.test_handle_signup_creates_user_and_session_cookie `
  scripts.test_web_workbench.WebWorkbenchTest.test_handle_account_change_password_updates_credentials `
  scripts.test_web_workbench.WebWorkbenchTest.test_handle_workspace_export_builds_backup_zip `
  scripts.test_web_workbench.WebWorkbenchTest.test_handle_runs_detail_returns_saved_payload_for_owner `
  scripts.test_mobile_api_contract.MobileAPIContractTest.test_login_session_and_case_list_over_http `
  scripts.test_mobile_api_contract.MobileAPIContractTest.test_mobile_case_list_rejects_missing_token
```

Expected: PASS. These tests cover the still-valid Web/mobile behavior that was duplicated in the adapter test file.

- [ ] **Step 2: Confirm runtime ownership before deletion**

```powershell
rg -n "class WorkbenchHandler|def create_server|MOBILE_API_PREFIX|handle_mobile_|handle_file_download" scripts/web_workbench.py
rg -n "import coze_api_server|from coze_api_server" scripts web-workbench ios-app -g '*.py' -g '*.js' -g '*.swift'
```

Expected: the standalone module owns the runtime endpoints; production consumers do not import the wrapper.

- [ ] **Step 3: Delete the adapter-only files**

Use `apply_patch` `*** Delete File` operations for the eight files listed under **Files**. Do not delete `scripts/web_workbench.py`, `scripts/hosted_smoke.py`, mobile API tests, Agent code, RAG, or document-generation code.

- [ ] **Step 4: Run standalone regressions after deletion**

```powershell
python -m unittest scripts.test_web_workbench scripts.test_mobile_api_contract scripts.test_deployment_contract scripts.test_hosted_smoke
```

Expected: PASS with no import of a deleted module.

- [ ] **Step 5: Commit**

```powershell
git add -A
git diff --cached --check
git commit -m "chore: remove the retired compatibility adapter"
```

---

### Task 5: Rewrite Product Documentation Around One Web Service

**Files:**
- Modify: `README.md`
- Modify: `docs/product-editions-and-directory-contract.md`
- Modify: `docs/product-loop-state.md`
- Modify: `docs/superpowers/plans/2026-07-02-market-validation-doc-freeze.md`
- Modify: `docs/superpowers/specs/2026-07-02-market-validation-doc-freeze-design.md`
- Modify: `ios-app/README.md`
- Modify: `ios-app/scripts/validate-package-boundary.ps1`

**Interfaces:**
- Consumes: the single-service deployment contract from Task 3
- Produces: documentation and package checks that describe only the standalone Web service and iOS client

- [ ] **Step 1: Demonstrate remaining repository references before editing**

```powershell
rg -n -i --hidden --glob '!.git/**' --glob '!.worktrees/**' --glob '!docs/superpowers/specs/2026-08-14-remove-coze-consolidate-web-design.md' --glob '!docs/superpowers/plans/2026-08-14-single-web-service-consolidation.md' 'coze|counselor-agent-coze-api|coze_demo_api_key' .
```

Expected: matches remain in current product/history documentation and iOS boundary checks.

- [ ] **Step 2: Rewrite `README.md` as a single-service product guide**

Use `apply_patch` to make these exact semantic changes:

- describe `ios-app/` as the native client and `web-workbench/` plus `scripts/web_workbench.py` as the retained hosted product;
- list only `counselor-agent-web` under Render deployment;
- state the canonical URL `https://counselor-agent-web.onrender.com`;
- state that smoke checks `/health`, `/api/session`, authentication, and optional `/api/run`;
- delete the compatibility API chapter, local wrapper command, tool routes, schema-generation command, shared-secret guidance, and old service URL.

Keep local Web startup, required Render variables, storage warning, hosted smoke examples, and privacy/de-identification guidance.

- [ ] **Step 3: Rewrite current product contracts and remove obsolete historical evidence**

In `docs/product-editions-and-directory-contract.md`:

- describe iOS and the independent hosted Web/API as the only supported product surfaces;
- remove compatibility schemas/adapters from the directory contract;
- retain the rule that iOS is a thin client and never bundles Python, RAG, `.env`, Web assets, or service secrets.

In `docs/product-loop-state.md`:

- change the current hosted URL to `https://counselor-agent-web.onrender.com`;
- replace current multi-channel statements with the single Web/API service contract;
- replace test command lists so they name `scripts.test_web_workbench` and `scripts.test_mobile_api_contract` only where applicable;
- remove obsolete wrapper file references and all old-host smoke/evidence bullets;
- retain non-obsolete W1-W6, iOS, Web, RAG, evaluation, safety, and document-generation evidence.

In the two 2026-07-02 plan/spec files, remove the obsolete deployment-document references while retaining any still-valid Web market-validation decisions.

- [ ] **Step 4: Simplify iOS documentation and boundary guards**

In `ios-app/README.md`, state that the native app calls the hosted product API at the canonical Web host and that Web assets, Python, RAG, `.env`, and local run data stay outside the app target.

In `ios-app/scripts/validate-package-boundary.ps1`, set:

```powershell
$forbiddenSegments = @("web-workbench", "agent-runs", "workbench-data", "eval-results", "rag")
$secretPattern = '(?i)(sk-[a-z0-9]{16,}|deepseek_api_key\s*=\s*[^$\s])'
```

Keep all other package-boundary checks unchanged.

- [ ] **Step 5: Verify that excluding the two transitional 2026-08-14 documents leaves no match**

```powershell
rg -n -i --hidden --glob '!.git/**' --glob '!.worktrees/**' --glob '!docs/superpowers/specs/2026-08-14-remove-coze-consolidate-web-design.md' --glob '!docs/superpowers/plans/2026-08-14-single-web-service-consolidation.md' 'coze|counselor-agent-coze-api|coze_demo_api_key' .
rg --files --hidden -g '!.git/**' -g '!.worktrees/**' | rg -i 'coze|counselor-agent-coze-api'
```

Expected: the content search returns no matches; the filename search returns only the transitional design file, which is removed in Task 8.

- [ ] **Step 6: Run documentation-adjacent tests and commit**

```powershell
python -m unittest scripts.test_deployment_contract scripts.test_hosted_smoke scripts.test_mobile_api_contract
powershell -NoProfile -ExecutionPolicy Bypass -File ios-app/scripts/validate-package-boundary.ps1
git add README.md docs ios-app/README.md ios-app/scripts/validate-package-boundary.ps1
git diff --cached --check
git commit -m "docs: document the standalone web product"
```

Expected: tests and package-boundary validation pass.

---

### Task 6: Run Complete Local Verification

**Files:**
- Verify: all `scripts/test_*.py`
- Verify: `web-workbench/app.js`
- Verify: `ios-app/`
- Verify: local `scripts/web_workbench.py` runtime

**Interfaces:**
- Consumes: the consolidated repository after Tasks 1-5
- Produces: local evidence that the single service still supports browser and mobile clients

- [ ] **Step 1: Run Python syntax and full unit-test discovery**

```powershell
$pythonFiles = Get-ChildItem scripts -Filter '*.py' -File | ForEach-Object { $_.FullName }
python -m py_compile $pythonFiles
python -m unittest discover -s scripts -p 'test_*.py'
```

Expected: syntax check and all discovered tests pass.

- [ ] **Step 2: Run frontend and iOS static validation**

```powershell
node --check web-workbench/app.js
powershell -NoProfile -ExecutionPolicy Bypass -File ios-app/scripts/validate-package-boundary.ps1
```

Expected: JavaScript syntax and iOS package boundary pass.

- [ ] **Step 3: Start the local standalone server and run an authenticated smoke**

```powershell
$mainEnvPath = (Resolve-Path '..\..\.env').Path
Get-Content -LiteralPath $mainEnvPath | ForEach-Object {
    $line = $_.Trim()
    if ($line -and -not $line.StartsWith('#') -and $line.Contains('=')) {
        $name, $value = $line.Split('=', 2)
        [Environment]::SetEnvironmentVariable($name.Trim(), $value.Trim(), 'Process')
    }
}
$server = Start-Process python -ArgumentList @('scripts/web_workbench.py', '--host', '127.0.0.1', '--port', '8765') -PassThru -WindowStyle Hidden
try {
    python scripts/hosted_smoke.py --base-url http://127.0.0.1:8765 --username demo --password demo123 --workflow AUTO --input '请根据这份脱敏材料整理下次咨询计划，保留风险检查点。' --expect-detected-workflow W5 --real-run --timeout 240
} finally {
    Stop-Process -Id $server.Id -ErrorAction SilentlyContinue
}
```

Expected: health, session, login, automatic routing, real model run, validation, and result response pass without printing the model-provider key.

- [ ] **Step 4: Verify local authenticated Word download through the standalone service**

Use the existing local browser testing workflow to log in with the demo account, run the synthetic de-identified prompt from Step 3, and download the generated Word artifact. Confirm HTTP 200, non-empty `.docx`, and no console error. Do not upload real counseling material.

- [ ] **Step 5: Commit any verification-driven fixes**

If verification exposed a defect, add only the affected production/test files and commit:

```powershell
$verificationChanges = @(git status --porcelain)
if ($verificationChanges.Count -gt 0) {
    git add -A
    git diff --cached --check
    git commit -m "fix: preserve standalone web workflow behavior"
}
```

If no defect was found, do not create an empty commit.

---

### Task 7: Configure the Canonical Render Service and Retire the Old Service

**Files:**
- External state: Render service `counselor-agent-web`
- External state: retired Render service `counselor-agent-coze-api`
- Verify only: repository `render.yaml`

**Interfaces:**
- Consumes: canonical service build from `codex/single-web-service`, a user-designated DeepSeek key, and user-designated workbench credentials
- Produces: a functional canonical deployment and removal of the obsolete hosted service

- [ ] **Step 1: Record the current canonical readiness without transmitting credentials**

```powershell
curl.exe -sS -L --max-time 30 https://counselor-agent-web.onrender.com/health
curl.exe -sS -L --max-time 30 https://counselor-agent-web.onrender.com/api/session
```

Expected before configuration: health is `ok`; readiness reports missing model access and default demo credentials.

- [ ] **Step 2: Request action-time confirmation for Render mutations**

Ask the user to confirm these exact external actions immediately before performing them:

1. transmit the user-designated `DEEPSEEK_API_KEY`, `WORKBENCH_USER`, and `WORKBENCH_PASSWORD` to the `counselor-agent-web` Render service;
2. push `codex/single-web-service` to `origin` and deploy that exact branch/commit;
3. permanently delete the obsolete Render service after the canonical smoke passes.

Do not display or log secret values.

- [ ] **Step 3: Configure and deploy the canonical service**

Push the reviewed branch, then configure and deploy it:

```powershell
git push -u origin codex/single-web-service
```

In the Render dashboard, verify the target service name is `counselor-agent-web`, select the pushed `codex/single-web-service` branch, then set the three confirmed secret variables. Keep the Blueprint-provided model base URL/model/timeout, signup policy, upload limit, and retention window. Deploy the consolidated commit and wait for `/health` to return HTTP 200.

- [ ] **Step 4: Run hosted product smoke against the canonical URL**

Use environment variables rather than literal credentials in the command:

```powershell
python scripts/hosted_smoke.py --base-url https://counselor-agent-web.onrender.com --username $env:COUNSELOR_SMOKE_USER --password $env:COUNSELOR_SMOKE_PASSWORD --workflow AUTO --input '请根据这份脱敏材料整理下次咨询计划，保留风险检查点。' --expect-detected-workflow W5 --expect-pilot-ready --real-run --timeout 240
```

Expected: readiness, authentication, real model run, and automatic route checks pass.

- [ ] **Step 5: Verify hosted Word download, then delete the obsolete service**

Use the browser with the canonical URL and confirmed test credentials. Run only synthetic de-identified material, download the generated `.docx`, and confirm HTTP 200 and non-empty content. Then verify the obsolete service target by exact service name and permanently delete it in Render.

- [ ] **Step 6: Verify post-deletion state**

Expected:

- `https://counselor-agent-web.onrender.com/health` remains HTTP 200;
- its authenticated workflow and Word download remain functional;
- the deleted service URL no longer serves the product;
- Render lists only the canonical Counselor Assistant Web service for this repository.

---

### Task 8: Remove Transitional Documents and Return a Clean Final Branch to the Main Workspace

**Files:**
- Delete: `docs/superpowers/specs/2026-08-14-remove-coze-consolidate-web-design.md`
- Delete: `docs/superpowers/plans/2026-08-14-single-web-service-consolidation.md`
- Verify: entire current worktree excluding `.git/` and `.worktrees/`

**Interfaces:**
- Consumes: all completed local and hosted tasks
- Produces: final zero-match repository, clean `codex/single-web-service` branch checked out in the main workspace, and retained recovery branch `codex/pre-single-web-snapshot`

- [ ] **Step 1: Delete the two transitional documents**

Use `apply_patch` `*** Delete File` operations for the design and implementation plan listed above.

- [ ] **Step 2: Remove only the verified tool-temporary directory from the original workspace**

From the linked implementation worktree, resolve and inspect the original workspace temporary directory before deleting it:

```powershell
$originalRoot = (Resolve-Path '..\..').Path
$temporaryRoot = (Resolve-Path (Join-Path $originalRoot '.superpowers')).Path
$expectedTemporaryRoot = Join-Path $originalRoot '.superpowers'
if ($temporaryRoot -ne $expectedTemporaryRoot) { throw 'Unexpected temporary directory path.' }
Get-ChildItem -LiteralPath $temporaryRoot -Recurse -Force
Remove-Item -LiteralPath $temporaryRoot -Recurse -Force
```

Expected before deletion: only brainstorming preview HTML and process-state files are present. Do not delete `.worktrees/` or any directory other than the exact verified `.superpowers` target.

- [ ] **Step 3: Run final zero-match checks**

```powershell
rg -n -i --hidden --glob '!.git/**' --glob '!.worktrees/**' 'coze|counselor-agent-coze-api|coze_demo_api_key' .
rg --files --hidden -g '!.git/**' -g '!.worktrees/**' | rg -i 'coze|counselor-agent-coze-api'
```

Expected: both commands return exit code 1 with no output, meaning no content or filename match remains in the current product worktree.

- [ ] **Step 4: Re-run the completion verification skill**

Invoke `superpowers:verification-before-completion`, then run:

```powershell
$pythonFiles = Get-ChildItem scripts -Filter '*.py' -File | ForEach-Object { $_.FullName }
python -m py_compile $pythonFiles
python -m unittest discover -s scripts -p 'test_*.py'
node --check web-workbench/app.js
powershell -NoProfile -ExecutionPolicy Bypass -File ios-app/scripts/validate-package-boundary.ps1
git diff --check
```

Expected: all commands pass.

- [ ] **Step 5: Commit final repository cleanup**

```powershell
git add -A
git diff --cached --check
git commit -m "chore: finalize the single-service repository"
git status --short
```

Expected: linked implementation worktree is clean.

- [ ] **Step 6: Move the finished branch back to the main workspace**

From the original repository root, first confirm the linked worktree is clean and resolve its absolute path under the intended `.worktrees` directory:

```powershell
$repoRoot = (Resolve-Path '.').Path
$finishedWorktree = (Resolve-Path '.worktrees/single-web-service').Path
if (-not $finishedWorktree.StartsWith((Join-Path $repoRoot '.worktrees'))) { throw 'Unexpected worktree path.' }
git -C $finishedWorktree status --porcelain
git worktree remove $finishedWorktree
git switch codex/single-web-service
git status --short --branch
rg -n -i --hidden --glob '!.git/**' --glob '!.worktrees/**' 'coze|counselor-agent-coze-api|coze_demo_api_key' .
rg --files --hidden -g '!.git/**' -g '!.worktrees/**' | rg -i 'coze|counselor-agent-coze-api'
```

Expected: the main workspace is on `codex/single-web-service`, clean, contains the finished repository, and both final search commands return no output. The recovery branch remains available until the user explicitly asks to remove it.
