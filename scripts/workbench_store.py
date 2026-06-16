import base64
import hashlib
import hmac
import os
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path


SESSION_DAYS = 7


class ClosingConnection(sqlite3.Connection):
    def __exit__(self, exc_type, exc_value, traceback):
        result = super().__exit__(exc_type, exc_value, traceback)
        self.close()
        return result


def utc_now():
    return datetime.now(timezone.utc)


def utc_iso():
    return utc_now().isoformat(timespec="seconds")


def parse_iso(value):
    return datetime.fromisoformat(value)


def hash_password(password, salt=None, iterations=200_000):
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return {
        "salt": base64.b64encode(salt).decode("ascii"),
        "hash": base64.b64encode(digest).decode("ascii"),
        "iterations": iterations,
    }


def verify_password(password, stored):
    try:
        salt = base64.b64decode(stored["salt"])
        expected = base64.b64decode(stored["hash"])
        iterations = int(stored["iterations"])
    except Exception:
        return False
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(digest, expected)


def row_to_dict(row):
    return dict(row) if row is not None else None


class WorkbenchStore:
    def __init__(self, db_path, upload_root):
        self.db_path = Path(db_path)
        self.upload_root = Path(upload_root)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.upload_root.mkdir(parents=True, exist_ok=True)
        self.init_db()

    def connect(self):
        conn = sqlite3.connect(self.db_path, factory=ClosingConnection)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        with self.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL UNIQUE,
                    password_salt TEXT NOT NULL,
                    password_hash TEXT NOT NULL,
                    password_iterations INTEGER NOT NULL,
                    role TEXT NOT NULL DEFAULT 'counselor',
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS sessions (
                    token TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    expires_at TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(user_id) REFERENCES users(id)
                );

                CREATE TABLE IF NOT EXISTS cases (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    client_code TEXT NOT NULL,
                    notes TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(user_id) REFERENCES users(id)
                );

                CREATE TABLE IF NOT EXISTS uploads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    case_id INTEGER,
                    original_name TEXT NOT NULL,
                    stored_path TEXT NOT NULL,
                    content_type TEXT NOT NULL DEFAULT '',
                    size_bytes INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(user_id) REFERENCES users(id),
                    FOREIGN KEY(case_id) REFERENCES cases(id)
                );

                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    case_id INTEGER,
                    action TEXT NOT NULL,
                    details TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(user_id) REFERENCES users(id),
                    FOREIGN KEY(case_id) REFERENCES cases(id)
                );
                """
            )
        self.ensure_default_user()

    def ensure_default_user(self):
        username = os.environ.get("WORKBENCH_USER", "demo")
        password = os.environ.get("WORKBENCH_PASSWORD", "demo123")
        with self.connect() as conn:
            exists = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
            if exists:
                return
            hashed = hash_password(password)
            conn.execute(
                """
                INSERT INTO users (
                    username, password_salt, password_hash, password_iterations, role, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    username,
                    hashed["salt"],
                    hashed["hash"],
                    hashed["iterations"],
                    "counselor",
                    utc_iso(),
                ),
            )

    def authenticate(self, username, password):
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
            if not row:
                return None
            stored = {
                "salt": row["password_salt"],
                "hash": row["password_hash"],
                "iterations": row["password_iterations"],
            }
            if not verify_password(password, stored):
                return None
            token = secrets.token_urlsafe(32)
            expires_at = (utc_now() + timedelta(days=SESSION_DAYS)).isoformat(timespec="seconds")
            conn.execute(
                "INSERT INTO sessions (token, user_id, expires_at, created_at) VALUES (?, ?, ?, ?)",
                (token, row["id"], expires_at, utc_iso()),
            )
            return {"token": token, "user": self.public_user(row), "expires_at": expires_at}

    def public_user(self, row):
        return {"id": row["id"], "username": row["username"], "role": row["role"]}

    def session_user(self, token):
        if not token:
            return None
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT users.*
                FROM sessions
                JOIN users ON users.id = sessions.user_id
                WHERE sessions.token = ? AND sessions.expires_at > ?
                """,
                (token, utc_iso()),
            ).fetchone()
            return self.public_user(row) if row else None

    def logout(self, token):
        with self.connect() as conn:
            conn.execute("DELETE FROM sessions WHERE token = ?", (token,))

    def create_case(self, user_id, title, client_code="", notes=""):
        now = utc_iso()
        with self.connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO cases (user_id, title, client_code, notes, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (user_id, title.strip() or "未命名个案", client_code.strip(), notes.strip(), now, now),
            )
            case_id = cursor.lastrowid
        self.audit(user_id, case_id, "case.create", {"title": title})
        return self.get_case(user_id, case_id)

    def list_cases(self, user_id):
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT id, title, client_code, notes, created_at, updated_at
                FROM cases
                WHERE user_id = ?
                ORDER BY updated_at DESC, id DESC
                """,
                (user_id,),
            ).fetchall()
            return [row_to_dict(row) for row in rows]

    def get_case(self, user_id, case_id):
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT id, title, client_code, notes, created_at, updated_at
                FROM cases
                WHERE user_id = ? AND id = ?
                """,
                (user_id, case_id),
            ).fetchone()
            return row_to_dict(row)

    def update_case(self, user_id, case_id, title=None, client_code=None, notes=None):
        current = self.get_case(user_id, case_id)
        if not current:
            return None
        next_title = current["title"] if title is None else title.strip() or current["title"]
        next_client_code = current["client_code"] if client_code is None else client_code.strip()
        next_notes = current["notes"] if notes is None else notes.strip()
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE cases
                SET title = ?, client_code = ?, notes = ?, updated_at = ?
                WHERE user_id = ? AND id = ?
                """,
                (next_title, next_client_code, next_notes, utc_iso(), user_id, case_id),
            )
        self.audit(user_id, case_id, "case.update", {"title": next_title})
        return self.get_case(user_id, case_id)

    def store_upload(self, user_id, original_name, content_b64, content_type="", case_id=None):
        binary = base64.b64decode(content_b64)
        safe_name = "".join(ch if ch.isalnum() or ch in ".-_ " else "_" for ch in original_name).strip()
        safe_name = safe_name or "upload.bin"
        case_part = f"case-{case_id}" if case_id else "unassigned"
        folder = self.upload_root / f"user-{user_id}" / case_part
        folder.mkdir(parents=True, exist_ok=True)
        target = folder / f"{utc_now().strftime('%Y%m%d%H%M%S')}-{secrets.token_hex(4)}-{safe_name}"
        target.write_bytes(binary)
        with self.connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO uploads (
                    user_id, case_id, original_name, stored_path, content_type, size_bytes, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (user_id, case_id, original_name, str(target), content_type, len(binary), utc_iso()),
            )
            upload_id = cursor.lastrowid
        self.audit(user_id, case_id, "file.upload", {"name": original_name, "size_bytes": len(binary)})
        return self.get_upload(user_id, upload_id)

    def get_upload(self, user_id, upload_id):
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT id, case_id, original_name, stored_path, content_type, size_bytes, created_at
                FROM uploads
                WHERE user_id = ? AND id = ?
                """,
                (user_id, upload_id),
            ).fetchone()
            return row_to_dict(row)

    def list_uploads(self, user_id, case_id=None):
        with self.connect() as conn:
            if case_id:
                rows = conn.execute(
                    """
                    SELECT id, case_id, original_name, stored_path, content_type, size_bytes, created_at
                    FROM uploads
                    WHERE user_id = ? AND case_id = ?
                    ORDER BY created_at DESC
                    """,
                    (user_id, case_id),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT id, case_id, original_name, stored_path, content_type, size_bytes, created_at
                    FROM uploads
                    WHERE user_id = ?
                    ORDER BY created_at DESC
                    """,
                    (user_id,),
                ).fetchall()
            return [row_to_dict(row) for row in rows]

    def audit(self, user_id, case_id, action, details=None):
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO audit_logs (user_id, case_id, action, details, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (user_id, case_id, action, json_dumps(details or {}), utc_iso()),
            )

    def list_audit_logs(self, user_id, limit=50, case_id=None):
        with self.connect() as conn:
            if case_id is not None:
                rows = conn.execute(
                    """
                    SELECT id, case_id, action, details, created_at
                    FROM audit_logs
                    WHERE user_id = ? AND case_id = ?
                    ORDER BY id DESC
                    LIMIT ?
                    """,
                    (user_id, case_id, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT id, case_id, action, details, created_at
                    FROM audit_logs
                    WHERE user_id = ?
                    ORDER BY id DESC
                    LIMIT ?
                    """,
                    (user_id, limit),
                ).fetchall()
            return [row_to_dict(row) for row in rows]


def json_dumps(value):
    import json

    return json.dumps(value, ensure_ascii=False, sort_keys=True)
