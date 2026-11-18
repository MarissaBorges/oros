"""Risk classification and approval queue for OROS actions."""

from __future__ import annotations

import json
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parent.parent
AUDIT_DB = ROOT / "data" / "guardian.sqlite3"


class Guardian:
    def __init__(self, db_path: Path = AUDIT_DB) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        connection = self._connection()
        connection.execute("""
            CREATE TABLE IF NOT EXISTS guardian_audit (
                id TEXT PRIMARY KEY,
                risk_level INTEGER NOT NULL,
                action TEXT NOT NULL,
                resource TEXT NOT NULL,
                status TEXT NOT NULL,
                reason TEXT,
                created_at REAL NOT NULL,
                resolved_at REAL
            )
        """)
        connection.commit()
        connection.close()

    def _connection(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def classify(self, action: str, resource: str = "") -> int:
        text = f"{action} {resource}".casefold()
        destructive = (
            "rm ", "rm -", "delete ", "trash ", "git push", "pacman -s",
            "pacman -r", "shutdown", "reboot", "poweroff", "send_email",
            "send email", "post ", "publish", "wipe", "mkfs", "dd if=",
        )
        reversible_write = (
            "create ", "write ", "edit ", "append ", "move ", "patch ",
            "open ", "focus ", "browser", "test ", "pytest", "npm ",
            "cargo ", "git add", "git commit", "git checkout",
        )
        if any(word in text for word in destructive):
            return 2
        if any(word in text for word in reversible_write):
            return 1
        return 0

    def authorize(
        self,
        action: str,
        resource: str = "",
        *,
        approved: bool = False,
        reason: str = "",
    ) -> dict:
        level = self.classify(action, resource)
        status = "approved" if level < 2 or approved else "pending"
        record_id = uuid.uuid4().hex
        connection = self._connection()
        connection.execute(
            "INSERT INTO guardian_audit "
            "(id,risk_level,action,resource,status,reason,created_at,resolved_at) "
            "VALUES(?,?,?,?,?,?,?,?)",
            (
                record_id,
                level,
                action,
                resource,
                status,
                reason,
                time.time(),
                time.time() if status == "approved" else None,
            ),
        )
        connection.commit()
        connection.close()
        return {
            "id": record_id,
            "risk_level": level,
            "status": status,
            "allowed": status == "approved",
        }

    def approve(self, record_id: str) -> dict:
        connection = self._connection()
        cursor = connection.execute(
            "UPDATE guardian_audit SET status='approved',resolved_at=? WHERE id=?",
            (time.time(), record_id),
        )
        connection.commit()
        connection.close()
        if cursor.rowcount == 0:
            return {"ok": False, "error": "Approval request not found"}
        return {"ok": True, "id": record_id, "status": "approved"}

    def pending(self) -> list[dict]:
        connection = self._connection()
        rows = connection.execute(
            "SELECT id,risk_level,action,resource,status,reason,created_at "
            "FROM guardian_audit WHERE status='pending' ORDER BY created_at DESC"
        ).fetchall()
        connection.close()
        return [
            {
                "id": row[0],
                "risk_level": row[1],
                "action": row[2],
                "resource": row[3],
                "status": row[4],
                "reason": row[5],
                "created_at": row[6],
            }
            for row in rows
        ]

    def audit(self, limit: int = 100) -> list[dict]:
        connection = self._connection()
        rows = connection.execute(
            "SELECT id,risk_level,action,resource,status,reason,created_at,resolved_at "
            "FROM guardian_audit ORDER BY created_at DESC LIMIT ?",
            (max(1, min(limit, 500)),),
        ).fetchall()
        connection.close()
        return [
            {
                "id": row[0],
                "risk_level": row[1],
                "action": row[2],
                "resource": row[3],
                "status": row[4],
                "reason": row[5],
                "created_at": row[6],
                "resolved_at": row[7],
            }
            for row in rows
        ]
