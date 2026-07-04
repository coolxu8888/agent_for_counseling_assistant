import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.workflow_completion import (
    GATE_IDS,
    CompletionValidationError,
    derive_workflow_status,
    render_markdown,
    replace_generated_section,
    validate_matrix,
)


class WorkflowCompletionTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.repo_root = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def gate(self, status="unverified", evidence=None):
        if evidence is None:
            evidence = []
        return {"status": status, "evidence": evidence}

    def workflow_with_statuses(self, statuses):
        return {
            "name": "Workflow",
            "gates": {
                gate_id: self.gate(status)
                for gate_id, status in zip(GATE_IDS, statuses, strict=True)
            },
        }

    def matrix(self):
        return {
            "schema_version": 1,
            "updated_at": "2026-07-04",
            "workflows": {
                f"W{index}": self.workflow_with_statuses(["unverified"] * 5)
                for index in range(1, 7)
            },
        }

    def assert_invalid(self, data, message):
        with self.assertRaisesRegex(CompletionValidationError, message):
            validate_matrix(data, self.repo_root)

    def test_all_five_passed_is_complete(self):
        workflow = self.workflow_with_statuses(["passed"] * 5)
        self.assertTrue(derive_workflow_status(workflow)["completed"])

    def test_any_non_passed_gate_is_incomplete(self):
        for status in ("failed", "unverified"):
            for missing_index, missing_gate in enumerate(GATE_IDS):
                with self.subTest(status=status, missing_gate=missing_gate):
                    statuses = ["passed"] * len(GATE_IDS)
                    statuses[missing_index] = status
                    derived = derive_workflow_status(
                        self.workflow_with_statuses(statuses)
                    )
                    self.assertFalse(derived["completed"])
                    self.assertEqual([missing_gate], derived["missing_gates"])

    def test_multiple_missing_gates_preserve_canonical_order(self):
        workflow = self.workflow_with_statuses(
            ["failed", "passed", "unverified", "passed", "failed"]
        )
        self.assertEqual(
            ["local_tests", "web_integration", "real_template_verification"],
            derive_workflow_status(workflow)["missing_gates"],
        )

    def test_rejects_missing_or_extra_workflows(self):
        data = self.matrix()
        del data["workflows"]["W6"]
        self.assert_invalid(data, "workflow keys")
        data = self.matrix()
        data["workflows"]["W7"] = data["workflows"]["W6"]
        self.assert_invalid(data, "workflow keys")

    def test_rejects_missing_or_extra_gates(self):
        data = self.matrix()
        del data["workflows"]["W1"]["gates"]["local_tests"]
        self.assert_invalid(data, "gate keys")
        data = self.matrix()
        data["workflows"]["W1"]["gates"]["manual_review"] = self.gate()
        self.assert_invalid(data, "gate keys")

    def test_rejects_unknown_status_and_manual_completed(self):
        data = self.matrix()
        data["workflows"]["W2"]["gates"]["local_tests"]["status"] = "pending"
        self.assert_invalid(data, "unsupported status")
        data = self.matrix()
        data["workflows"]["W2"]["completed"] = False
        self.assert_invalid(data, "completed")

    def test_rejects_completed_nested_in_gate_or_evidence_but_allows_note(self):
        data = self.matrix()
        data["workflows"]["W1"]["gates"]["local_tests"]["completed"] = True
        self.assert_invalid(data, "completed")

        data = self.matrix()
        gate = data["workflows"]["W1"]["gates"]["local_tests"]
        gate["note"] = "Waiting for a durable result."
        gate["evidence"] = [
            {
                "type": "command",
                "value": "python -m unittest",
                "completed": True,
            }
        ]
        self.assert_invalid(data, "completed")

        del gate["evidence"][0]["completed"]
        validate_matrix(data, self.repo_root)

    def test_rejects_passed_gate_without_evidence(self):
        data = self.matrix()
        data["workflows"]["W3"]["gates"]["local_tests"]["status"] = "passed"
        self.assert_invalid(data, "non-empty evidence")

    def test_rejects_missing_or_escaping_local_evidence_path(self):
        data = self.matrix()
        gate = data["workflows"]["W1"]["gates"]["local_tests"]
        gate.update(status="passed", evidence=[{"type": "path", "value": "missing.txt"}])
        self.assert_invalid(data, "does not exist")

        outside = self.repo_root.parent / "outside-evidence.txt"
        outside.write_text("proof", encoding="utf-8")
        self.addCleanup(outside.unlink, missing_ok=True)
        gate["evidence"] = [{"type": "path", "value": "../outside-evidence.txt"}]
        self.assert_invalid(data, "outside repository")

    def test_accepts_valid_passed_evidence(self):
        evidence = self.repo_root / "results" / "w1.txt"
        evidence.parent.mkdir()
        evidence.write_text("pass", encoding="utf-8")
        data = self.matrix()
        data["workflows"]["W1"]["gates"]["local_tests"] = self.gate(
            "passed",
            [
                {"type": "path", "value": "results/w1.txt"},
                {"type": "command", "value": "python -m unittest"},
            ],
        )
        validate_matrix(data, self.repo_root)

    def test_accepts_hosted_url_evidence_without_network_access(self):
        data = self.matrix()
        data["workflows"]["W4"]["gates"]["hosted_verification"] = self.gate(
            "passed",
            [{"type": "url", "value": "https://example.invalid/runs/w4"}],
        )
        validate_matrix(data, self.repo_root)

    def test_render_markdown_has_workflows_gates_and_derived_state(self):
        data = self.matrix()
        data["workflows"]["W1"] = self.workflow_with_statuses(["passed"] * 5)
        rendered = render_markdown(data)
        for workflow_id in (f"W{i}" for i in range(1, 7)):
            self.assertIn(f"| {workflow_id} |", rendered)
        for gate_id in GATE_IDS:
            self.assertIn(gate_id, rendered)
        self.assertIn("完成", rendered)
        self.assertIn("local_tests", rendered)

    def test_replace_generated_section_and_reject_bad_markers(self):
        document = "before\n<!-- workflow-completion:start -->\nstale\n<!-- workflow-completion:end -->\nafter\n"
        expected = "before\n<!-- workflow-completion:start -->\nfresh\n<!-- workflow-completion:end -->\nafter\n"
        self.assertEqual(expected, replace_generated_section(document, "fresh"))
        with self.assertRaisesRegex(CompletionValidationError, "markers"):
            replace_generated_section("no markers", "fresh")
        with self.assertRaisesRegex(CompletionValidationError, "markers"):
            replace_generated_section(document + document, "fresh")

    def test_cli_check_detects_drift_and_write_repairs_it(self):
        data = self.matrix()
        matrix_path = self.repo_root / "matrix.json"
        document_path = self.repo_root / "progress.md"
        matrix_path.write_text(json.dumps(data), encoding="utf-8")
        document_path.write_text(
            "<!-- workflow-completion:start -->\nstale\n<!-- workflow-completion:end -->\n",
            encoding="utf-8",
        )
        script = Path(__file__).with_name("workflow_completion.py")
        common = [
            sys.executable,
            str(script),
            "--matrix",
            str(matrix_path),
            "--document",
            str(document_path),
        ]
        checked = subprocess.run(common + ["--check"], text=True, capture_output=True)
        self.assertEqual(1, checked.returncode)
        self.assertIn("--write", checked.stderr)
        written = subprocess.run(common + ["--write"], text=True, capture_output=True)
        self.assertEqual(0, written.returncode, written.stderr)
        checked = subprocess.run(common + ["--check"], text=True, capture_output=True)
        self.assertEqual(0, checked.returncode, checked.stderr)


if __name__ == "__main__":
    unittest.main()
