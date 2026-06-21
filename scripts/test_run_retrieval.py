import json
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run-retrieval.ps1"


class RunRetrievalTest(unittest.TestCase):
    def run_retrieval(self, query):
        completed = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(SCRIPT),
                "-Query",
                query,
                "-SummaryOnly",
                "-Json",
            ],
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        return json.loads(completed.stdout)

    def test_routes_next_session_plan_query_to_w5(self):
        payload = self.run_retrieval(
            "Create a CBT next-session plan for this de-identified case with risk check points."
        )

        self.assertEqual(payload["status"], "OK")
        self.assertEqual(payload["route"]["workflow"], "workflow_5_next_session_plan")
        chunk_ids = [chunk["chunk_id"] for chunk in payload["selected_chunks"]]
        self.assertIn("next-session-planning-bounded-next-session-plan-001", chunk_ids)


if __name__ == "__main__":
    unittest.main()
