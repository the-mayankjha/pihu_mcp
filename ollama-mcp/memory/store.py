import sqlite3
from pathlib import Path


DB_PATH = Path(__file__).parent.parent / "data" / "memory.db"


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(DB_PATH) as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        db.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL UNIQUE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)


def save_message(role: str, content: str):
    with sqlite3.connect(DB_PATH) as db:
        db.execute(
            "INSERT INTO messages (role, content) VALUES (?, ?)",
            (role, content),
        )


def save_memory(content: str):
    content = content.strip()

    if not content:
        return

    with sqlite3.connect(DB_PATH) as db:
        db.execute(
            "INSERT OR IGNORE INTO memories (content) VALUES (?)",
            (content,),
        )


def get_recent_messages(limit: int = 12):
    with sqlite3.connect(DB_PATH) as db:
        rows = db.execute(
            """
            SELECT role, content
            FROM messages
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    return list(reversed(rows))


def search_memories(query: str, limit: int = 5):
    words = [
        word.strip().lower()
        for word in query.split()
        if len(word.strip()) >= 3
    ]

    if not words:
        return []

    results = []

    with sqlite3.connect(DB_PATH) as db:
        for word in words:
            rows = db.execute(
                """
                SELECT content
                FROM memories
                WHERE content LIKE ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (f"%{word}%", limit),
            ).fetchall()

            results.extend(row[0] for row in rows)

    # Remove duplicates while preserving order
    return list(dict.fromkeys(results))[:limit]
