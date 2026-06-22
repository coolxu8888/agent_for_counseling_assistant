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

    def test_routes_counseling_roadmap_query_to_w6(self):
        payload = self.run_retrieval(
            "Create an integrative counseling roadmap for this de-identified case with phases, hypotheses to verify, and risk monitoring checkpoints."
        )

        self.assertEqual(payload["status"], "OK")
        self.assertEqual(payload["route"]["workflow"], "workflow_6_counseling_roadmap")
        chunk_ids = [chunk["chunk_id"] for chunk in payload["selected_chunks"]]
        self.assertIn("roadmap-planning-bounded-counseling-roadmap-001", chunk_ids)

    def test_routes_pre_interview_collection_query_to_w1(self):
        payload = self.run_retrieval(
            "Before tomorrow's first interview, create an intake question guide for what information still needs to be collected."
        )

        self.assertEqual(payload["status"], "OK")
        self.assertEqual(payload["route"]["workflow"], "workflow_1_intake_form")

    def test_routes_post_session_note_query_to_w3_even_when_it_mentions_first_interview(self):
        payload = self.run_retrieval(
            "These are my first interview notes from today. Turn them into a counseling record with a risk update and next session focus."
        )

        self.assertEqual(payload["status"], "OK")
        self.assertEqual(payload["route"]["workflow"], "workflow_3_session_note")

    def test_routes_mixed_next_session_and_roadmap_query_to_w6(self):
        payload = self.run_retrieval(
            "Map the next several sessions into a phased counseling roadmap, including the immediate next session and later phases."
        )

        self.assertEqual(payload["status"], "OK")
        self.assertEqual(payload["route"]["workflow"], "workflow_6_counseling_roadmap")


if __name__ == "__main__":
    unittest.main()
