"""SQLite-backed persisted successful tool results for single-host deployments.

WARNING: get/put does not atomically claim in-flight operations. For money-moving
or external writes use an atomic reservation/lease and downstream idempotency.
Do not treat persistence alone as exactly-once execution.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from .governed_tool_call import ToolResult


class SQLiteIdempotencyStore:
    def __init__(self, path: str | Path) -> None:
        self.path = str(path)
        with self._connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS idempotency (key TEXT PRIMARY KEY, result TEXT NOT NULL)")

    def _connect(self):
        db = sqlite3.connect(self.path, timeout=30)
        db.execute("PRAGMA busy_timeout=30000")
        return db

    def get(self, key: str) -> ToolResult | None:
        with self._connect() as db:
            row = db.execute("SELECT result FROM idempotency WHERE key=?", (key,)).fetchone()
        if row is None:
            return None
        data = json.loads(row[0])
        return ToolResult(**data)

    def put(self, key: str, result: ToolResult) -> None:
        payload = json.dumps({"ok": result.ok, "data": result.data, "operation_id": result.operation_id}, sort_keys=True)
        with self._connect() as db:
            db.execute("INSERT OR IGNORE INTO idempotency (key, result) VALUES (?,?)", (key, payload))
