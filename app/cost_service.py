import os
import sqlite3
from pathlib import Path
from threading import Lock

_GPT4O_INPUT_PER_1K = 0.005
_GPT4O_OUTPUT_PER_1K = 0.015

class CostService:
    _instance = None
    _class_lock = Lock()

    def __new__(cls):
        with cls._class_lock:
            if cls._instance is None:
                instance = super().__new__(cls)
                instance._initialized = False
                cls._instance = instance
        return cls._instance

    def __init__(self):
        with self.__class__._class_lock:
            if self._initialized:
                return
            db_path = os.getenv("COST_DB_PATH", "workspace/aaplamanus.db")
            if db_path != ":memory:":
                Path(db_path).parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(db_path, check_same_thread=False)
            self._lock = Lock()
            self._init_schema()
            self._initialized = True

    def _init_schema(self):
        with self._lock:
            self._conn.executescript("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    started_at TEXT NOT NULL DEFAULT (datetime('now')),
                    total_tokens INTEGER DEFAULT 0,
                    total_saved_usd REAL DEFAULT 0.0
                );
                CREATE TABLE IF NOT EXISTS token_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    agent TEXT NOT NULL,
                    model TEXT NOT NULL,
                    input_tokens INTEGER NOT NULL,
                    output_tokens INTEGER NOT NULL,
                    saved_usd REAL NOT NULL,
                    timestamp TEXT NOT NULL DEFAULT (datetime('now'))
                );
            """)
            self._conn.commit()

    def log(
        self,
        session_id: str,
        agent: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        saved = (input_tokens / 1000 * _GPT4O_INPUT_PER_1K) + (
            output_tokens / 1000 * _GPT4O_OUTPUT_PER_1K
        )
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO sessions (id, total_tokens, total_saved_usd)
                VALUES (?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    total_tokens = total_tokens + excluded.total_tokens,
                    total_saved_usd = total_saved_usd + excluded.total_saved_usd
                """,
                (session_id, input_tokens + output_tokens, saved),
            )
            self._conn.execute(
                """
                INSERT INTO token_log
                    (session_id, agent, model, input_tokens, output_tokens, saved_usd)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (session_id, agent, model, input_tokens, output_tokens, saved),
            )
            self._conn.commit()
        return saved

    def get_stats(self, session_id: str = None) -> dict:
        with self._lock:
            row = self._conn.execute(
                "SELECT COALESCE(SUM(total_saved_usd),0), COALESCE(SUM(total_tokens),0) FROM sessions"
            ).fetchone()
            task_count = self._conn.execute(
                "SELECT COUNT(*) FROM token_log"
            ).fetchone()[0]
            session_saved = 0.0
            if session_id:
                r = self._conn.execute(
                    "SELECT total_saved_usd FROM sessions WHERE id = ?", (session_id,)
                ).fetchone()
                if r:
                    session_saved = r[0]
            top = self._conn.execute(
                "SELECT agent FROM token_log GROUP BY agent ORDER BY COUNT(*) DESC LIMIT 1"
            ).fetchone()
        return {
            "session_saved_usd": round(session_saved, 2),
            "alltime_saved_usd": round(row[0], 2),
            "alltime_tokens": row[1],
            "tasks_completed": task_count,
            "most_used_agent": top[0] if top else None,
        }


cost_service = CostService()
