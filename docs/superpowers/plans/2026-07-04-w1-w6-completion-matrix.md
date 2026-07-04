# W1-W6 Unified Completion Matrix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build one machine-checkable W1-W6 completion matrix where all five gates must pass before a workflow is derived as complete, and surface that matrix in the repository's existing progress-management documents.

**Architecture:** Store gate facts and evidence in a root-level JSON file without a writable completion flag. A focused Python module validates the schema, derives completion and next missing gates, and renders a marked Markdown section. Unit tests define the rules; the checked-in matrix section in `docs/product-loop-state.md` is generated from the JSON, while `README.md` links readers to that single progress source.

**Tech Stack:** Python 3 standard library, JSON, `unittest`, Markdown, existing PowerShell/Python developer workflow.

---

## File Map

- Create `workflow-completion.json`: authoritative W1-W6 gate status and evidence.
- Create `scripts/workflow_completion.py`: validation, completion derivation, Markdown rendering, check/write CLI.
- Create `scripts/test_workflow_completion.py`: rule and document-drift tests.
- Modify `docs/product-loop-state.md`: generated matrix plus short update workflow; existing history remains intact.
- Modify `README.md`: link to the authoritative progress section and show the validation command.

### Task 1: Define and enforce the completion model

**Files:**
- Create: `scripts/test_workflow_completion.py`
- Create: `scripts/workflow_completion.py`

- [ ] **Step 1: Write failing model tests**

Add tests that build an in-memory matrix and assert:

```python
def test_all_five_passed_is_complete(self):
    workflow = self.workflow_with_statuses(["passed"] * 5)
    self.assertTrue(derive_workflow_status(workflow)["completed"])

def test_any_non_passed_gate_is_incomplete(self):
    for status in ("failed", "unverified"):
        workflow = self.workflow_with_statuses(
            ["passed", "passed", "passed", "passed", status]
        )
        derived = derive_workflow_status(workflow)
        self.assertFalse(derived["completed"])
        self.assertEqual(["real_template_verification"], derived["missing_gates"])
```

Also test rejection of missing/extra workflows, missing/extra gates, unknown statuses, a `passed` gate without evidence, and any stored `completed` key.

- [ ] **Step 2: Run the tests and verify red**

Run:

```powershell
$env:PYTHONPATH='scripts'; python -m unittest scripts.test_workflow_completion -v
```

Expected: FAIL because `scripts.workflow_completion` does not exist.

- [ ] **Step 3: Implement the minimal model**

In `scripts/workflow_completion.py`, define:

```python
WORKFLOW_IDS = tuple(f"W{index}" for index in range(1, 7))
GATE_IDS = (
    "local_tests",
    "real_model_eval",
    "web_integration",
    "hosted_verification",
    "real_template_verification",
)
VALID_STATUSES = {"passed", "failed", "unverified"}

class CompletionValidationError(ValueError):
    pass

def validate_matrix(data: dict, repo_root: Path) -> None:
    """Reject schema drift, unsupported claims, and missing evidence."""

def derive_workflow_status(workflow: dict) -> dict:
    missing = [gate for gate in GATE_IDS if workflow["gates"][gate]["status"] != "passed"]
    return {"completed": not missing, "missing_gates": missing}
```

Use exact-key comparisons for workflows and gates. Reject `completed` anywhere in a workflow record. Require a non-empty evidence list for `passed`. For evidence objects with `type: "path"`, resolve `value` below `repo_root` and require it to exist.

- [ ] **Step 4: Run the model tests and verify green**

Run the command from Step 2.

Expected: all model tests PASS.

- [ ] **Step 5: Commit the model**

```powershell
git add scripts/workflow_completion.py scripts/test_workflow_completion.py
git commit -m "Add W1-W6 completion model"
```

### Task 2: Add the conservative source-of-truth matrix

**Files:**
- Create: `workflow-completion.json`
- Modify: `scripts/test_workflow_completion.py`

- [ ] **Step 1: Write a failing repository-file test**

```python
def test_repository_matrix_is_valid(self):
    repo_root = Path(__file__).resolve().parents[1]
    data = load_matrix(repo_root / "workflow-completion.json")
    validate_matrix(data, repo_root)
    self.assertEqual({f"W{i}" for i in range(1, 7)}, set(data["workflows"]))
```

- [ ] **Step 2: Run the test and verify red**

Run:

```powershell
$env:PYTHONPATH='scripts'; python -m unittest scripts.test_workflow_completion.WorkflowCompletionTest.test_repository_matrix_is_valid -v
```

Expected: FAIL because `workflow-completion.json` does not exist.

- [ ] **Step 3: Create the initial JSON matrix**

Create schema version 1 with W1-W6 and all five gates. Begin each gate as `unverified` unless repository evidence has been inspected and satisfies the design's workflow-level standard. Use this shape:

```json
{
  "schema_version": 1,
  "updated_at": "2026-07-04",
  "workflows": {
    "W1": {
      "name": "Initial interview",
      "gates": {
        "local_tests": {"status": "unverified", "evidence": []},
        "real_model_eval": {"status": "unverified", "evidence": []},
        "web_integration": {"status": "unverified", "evidence": []},
        "hosted_verification": {"status": "unverified", "evidence": []},
        "real_template_verification": {"status": "unverified", "evidence": []}
      }
    }
  }
}
```

Repeat the complete gate object for W2-W6; do not add `completed`.

- [ ] **Step 4: Inspect and migrate only sufficient evidence**

Search `docs/product-loop-state.md`, `eval-results/`, test files, and hosted smoke commands for each workflow/gate. A passing claim must point to a reproducible command or committed result/path. Keep ambiguous items `unverified`; add a short `note` explaining the missing proof.

- [ ] **Step 5: Run the full unit test and verify green**

```powershell
$env:PYTHONPATH='scripts'; python -m unittest scripts.test_workflow_completion -v
```

Expected: PASS.

- [ ] **Step 6: Commit the matrix**

```powershell
git add workflow-completion.json scripts/test_workflow_completion.py
git commit -m "Add authoritative workflow completion data"
```

### Task 3: Generate and check the human-readable matrix

**Files:**
- Modify: `scripts/workflow_completion.py`
- Modify: `scripts/test_workflow_completion.py`
- Modify: `docs/product-loop-state.md`

- [ ] **Step 1: Write failing renderer and drift tests**

Test that rendering includes all six workflow rows, five gates, a derived overall state, and the first missing gate. Add a temporary-document test asserting check mode fails when content between markers differs:

```markdown
<!-- workflow-completion:start -->
<!-- workflow-completion:end -->
```

- [ ] **Step 2: Run the focused tests and verify red**

```powershell
$env:PYTHONPATH='scripts'; python -m unittest scripts.test_workflow_completion -v
```

Expected: FAIL because rendering/check functions are absent.

- [ ] **Step 3: Implement renderer and CLI**

Add:

```python
def render_markdown(data: dict) -> str:
    """Render a compact Chinese table from validated matrix data."""

def replace_generated_section(document: str, rendered: str) -> str:
    """Replace only content inside the two completion markers."""

def main(argv: Sequence[str] | None = None) -> int:
    """Support --check for drift and --write for regeneration."""
```

CLI behavior:

```powershell
python scripts/workflow_completion.py --write
python scripts/workflow_completion.py --check
```

`--write` updates only the marked section. `--check` returns exit code 1 with a clear regeneration command when JSON is invalid or the document is stale.

- [ ] **Step 4: Add the generated section to the progress file**

Place a `## W1-W6 Unified Completion Matrix` section near `Current Capability Backlog`. Explain in plain Chinese that five checks must all pass, then add the start/end markers and run `--write`.

- [ ] **Step 5: Run tests and document check**

```powershell
$env:PYTHONPATH='scripts'; python -m unittest scripts.test_workflow_completion -v
python scripts/workflow_completion.py --check
```

Expected: all tests PASS and the check exits 0.

- [ ] **Step 6: Commit the generated matrix**

```powershell
git add scripts/workflow_completion.py scripts/test_workflow_completion.py docs/product-loop-state.md
git commit -m "Generate workflow completion progress matrix"
```

### Task 4: Make the matrix the visible project-management entry point

**Files:**
- Modify: `README.md`
- Modify: `docs/product-loop-state.md`
- Modify: `scripts/test_workflow_completion.py`

- [ ] **Step 1: Write a failing documentation contract test**

Assert README mentions `workflow-completion.json`, links to `docs/product-loop-state.md`, and shows `python scripts/workflow_completion.py --check`. Assert the progress file explains the update loop: verify, record evidence, regenerate, check.

- [ ] **Step 2: Run the test and verify red**

```powershell
$env:PYTHONPATH='scripts'; python -m unittest scripts.test_workflow_completion -v
```

Expected: FAIL on the missing README/progress contract.

- [ ] **Step 3: Add concise documentation**

In README, add a short “项目完成度” entry pointing to the existing progress file and the check command. In `docs/product-loop-state.md`, make W1-W6 narrative backlog rows refer to the generated matrix for authoritative completion status; preserve narrative evidence and remaining-gap history.

- [ ] **Step 4: Run repository verification**

```powershell
$env:PYTHONPATH='scripts'; python -m unittest scripts.test_workflow_completion -v
python scripts/workflow_completion.py --check
python -m unittest discover -s scripts -p 'test_*.py'
git diff --check
```

Expected: all tests PASS, matrix check exits 0, and no whitespace errors are reported.

- [ ] **Step 5: Review derived results**

Read the generated W1-W6 table. Confirm no workflow is shown complete unless every gate says passed and each passed gate contains sufficient evidence. Confirm unknown items remain visibly unverified with a next missing gate.

- [ ] **Step 6: Commit the integration**

```powershell
git add README.md docs/product-loop-state.md scripts/test_workflow_completion.py
git commit -m "Integrate workflow matrix into project progress"
```

## Final Acceptance

- [ ] `workflow-completion.json` contains exactly W1-W6 and exactly five gates each.
- [ ] No manually writable workflow completion field exists.
- [ ] Any non-passed gate derives an incomplete workflow.
- [ ] Passed gates require evidence; claimed local paths exist.
- [ ] `docs/product-loop-state.md` contains a generated, current matrix.
- [ ] README points to the single authoritative progress location.
- [ ] Unit tests, full script test discovery, matrix check, and `git diff --check` pass.
- [ ] The Notion overview remains a plain-language presentation layer; repository state remains authoritative.
