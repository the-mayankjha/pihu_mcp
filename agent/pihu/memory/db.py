"""
PIHU SQLite Database & Activity Index — Persistent SQLite storage at ~/.pihu/pihu.db
Stores sessions, messages, memories, projects, and lightweight activity tracking events.
"""

import json
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
import aiosqlite
from pihu.config.settings import settings


class PihuDatabase:
    """SQLite storage engine managing sessions, memories, activity history, and project index."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or settings.db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    async def initialize(self) -> None:
        """Initialize database schema tables."""
        async with aiosqlite.connect(self.db_path) as db:
            # Sessions table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    provider TEXT,
                    model TEXT,
                    created_at REAL,
                    updated_at REAL
                )
            """)

            # Messages table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    role TEXT,
                    content TEXT,
                    tool_calls_json TEXT,
                    timestamp REAL,
                    FOREIGN KEY(session_id) REFERENCES sessions(id)
                )
            """)

            # Activity tracking event log
            await db.execute("""
                CREATE TABLE IF NOT EXISTS activities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT,
                    target TEXT,
                    details_json TEXT,
                    timestamp REAL
                )
            """)

            # Fast Project index
            await db.execute("""
                CREATE TABLE IF NOT EXISTS projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE,
                    path TEXT,
                    language TEXT,
                    git_enabled INTEGER,
                    last_worked_on REAL
                )
            """)

            # Memories & Facts
            await db.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT UNIQUE,
                    value TEXT,
                    category TEXT,
                    created_at REAL
                )
            """)

            await db.commit()

    async def record_activity(self, event_type: str, target: str, details: Optional[Dict[str, Any]] = None) -> None:
        """Record lightweight activity event (e.g. FILE_READ, PROJECT_OPENED, TOOL_EXECUTED)."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO activities (event_type, target, details_json, timestamp) VALUES (?, ?, ?, ?)",
                (event_type, target, json.dumps(details or {}), time.time())
            )
            await db.commit()

    async def get_recent_activities(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieve recent activity logs."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT event_type, target, details_json, timestamp FROM activities ORDER BY timestamp DESC LIMIT ?",
                (limit,)
            ) as cursor:
                rows = await cursor.fetchall()
                return [
                    {
                        "event_type": row["event_type"],
                        "target": row["target"],
                        "details": json.loads(row["details_json"]),
                        "timestamp": row["timestamp"]
                    }
                    for row in rows
                ]

    async def index_project(self, name: str, path: str, language: str = "", git_enabled: bool = True) -> None:
        """Add or update project index entry."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO projects (name, path, language, git_enabled, last_worked_on)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    path=excluded.path,
                    language=excluded.language,
                    git_enabled=excluded.git_enabled,
                    last_worked_on=excluded.last_worked_on
            """, (name, path, language, 1 if git_enabled else 0, time.time()))
            await db.commit()

    async def get_recent_projects(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Retrieve recently worked on projects from SQLite index."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT name, path, language, git_enabled, last_worked_on FROM projects ORDER BY last_worked_on DESC LIMIT ?",
                (limit,)
            ) as cursor:
                rows = await cursor.fetchall()
                return [
                    {
                        "name": row["name"],
                        "path": row["path"],
                        "language": row["language"],
                        "git_enabled": bool(row["git_enabled"]),
                        "last_worked_on": row["last_worked_on"]
                    }
                    for row in rows
                ]

    async def set_memory(self, key: str, value: str, category: str = "fact") -> None:
        """Store a fact or preference in persistent SQLite memory."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO memories (key, value, category, created_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET value=excluded.value, created_at=excluded.created_at
            """, (key, value, category, time.time()))
            await db.commit()

    async def get_memory(self, key: str) -> Optional[str]:
        """Retrieve stored memory by key."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT value FROM memories WHERE key = ?", (key,)) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else None


# Shared database singleton
db_engine = PihuDatabase()
