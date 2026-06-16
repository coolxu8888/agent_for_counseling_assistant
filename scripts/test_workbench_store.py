import base64
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from workbench_store import WorkbenchStore


class WorkbenchStoreTest(unittest.TestCase):
    def make_store(self, tmp):
        root = Path(tmp)
        return WorkbenchStore(root / "workbench.sqlite3", root / "uploads")

    def test_authenticate_default_user_and_session_lookup(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = self.make_store(tmp)

            auth = store.authenticate("demo", "demo123")
            user = store.session_user(auth["token"])

        self.assertEqual(auth["user"]["username"], "demo")
        self.assertEqual(user["username"], "demo")

    def test_create_case_list_and_update_case(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = self.make_store(tmp)
            auth = store.authenticate("demo", "demo123")
            user_id = auth["user"]["id"]

            case_record = store.create_case(user_id, "初访个案", client_code="A001")
            updated = store.update_case(user_id, case_record["id"], notes="去识别笔记")
            cases = store.list_cases(user_id)

        self.assertEqual(updated["notes"], "去识别笔记")
        self.assertEqual(cases[0]["client_code"], "A001")

    def test_store_upload_and_audit_log(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = self.make_store(tmp)
            auth = store.authenticate("demo", "demo123")
            user_id = auth["user"]["id"]
            case_record = store.create_case(user_id, "初访个案")

            upload = store.store_upload(
                user_id,
                "template.docx",
                base64.b64encode(b"docx").decode("ascii"),
                case_id=case_record["id"],
            )
            logs = store.list_audit_logs(user_id)

            self.assertTrue(Path(upload["stored_path"]).exists())
            self.assertEqual(upload["size_bytes"], 4)
            self.assertTrue(any(item["action"] == "file.upload" for item in logs))

    def test_register_run_artifact_tracks_owner_and_case(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = self.make_store(tmp)
            auth = store.authenticate("demo", "demo123")
            user_id = auth["user"]["id"]
            case_record = store.create_case(user_id, "Run Case")
            run_dir = Path(tmp) / "agent-runs" / "run-1"
            run_dir.mkdir(parents=True)

            store.register_run_artifact(
                user_id,
                str(run_dir),
                workflow="W3",
                case_id=case_record["id"],
                source_action="workflow.run",
            )
            record = store.get_run_artifact(user_id, str(run_dir))

        self.assertEqual(record["workflow"], "W3")
        self.assertEqual(record["case_id"], case_record["id"])
        self.assertEqual(record["source_action"], "workflow.run")

    def test_list_run_artifacts_returns_case_scoped_runs_newest_first(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = self.make_store(tmp)
            auth = store.authenticate("demo", "demo123")
            user_id = auth["user"]["id"]
            case_a = store.create_case(user_id, "Case A")
            case_b = store.create_case(user_id, "Case B")
            run_root = Path(tmp) / "agent-runs"
            run_one = run_root / "run-1"
            run_two = run_root / "run-2"
            run_three = run_root / "run-3"
            run_one.mkdir(parents=True)
            run_two.mkdir(parents=True)
            run_three.mkdir(parents=True)

            store.register_run_artifact(user_id, str(run_one), workflow="W1", case_id=case_a["id"], source_action="workflow.run")
            store.register_run_artifact(user_id, str(run_two), workflow="W3", case_id=case_a["id"], source_action="template.draft")
            store.register_run_artifact(user_id, str(run_three), workflow="W2", case_id=case_b["id"], source_action="workflow.run")

            case_a_runs = store.list_run_artifacts(user_id, case_id=case_a["id"])
            all_runs = store.list_run_artifacts(user_id)

        self.assertEqual([item["run_dir"] for item in case_a_runs], [str(run_two.resolve()), str(run_one.resolve())])
        self.assertEqual(case_a_runs[0]["workflow"], "W3")
        self.assertEqual(len(all_runs), 3)


if __name__ == "__main__":
    unittest.main()
