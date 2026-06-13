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


if __name__ == "__main__":
    unittest.main()
