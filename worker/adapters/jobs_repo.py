import sqlite3
from datetime import datetime, timezone
from pathlib import Path


class SQLiteJobsRepository:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self._ensure_parent_directory()
        self._init_schema()

    def _ensure_parent_directory(self) -> None:
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _init_schema(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    job_id TEXT PRIMARY KEY,
                    input_key TEXT NOT NULL,
                    status TEXT NOT NULL,
                    error TEXT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS job_variants (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    width INTEGER NOT NULL,
                    format TEXT NOT NULL,
                    status TEXT NOT NULL,
                    output_key TEXT NULL,
                    error TEXT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(job_id, name),
                    FOREIGN KEY(job_id) REFERENCES jobs(job_id)
                )
                """
            )
            connection.commit()

    def update_job_status(self, job_id: str, status: str, error: str | None = None) -> None:
        timestamp = _utc_now_iso()
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE jobs
                SET status = ?, error = ?, updated_at = ?
                WHERE job_id = ?
                """,
                (status, error, timestamp, job_id),
            )
            connection.commit()

    def update_variant_status(
        self,
        job_id: str,
        variant_name: str,
        status: str,
        output_key: str | None = None,
        error: str | None = None,
    ) -> None:
        timestamp = _utc_now_iso()
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE job_variants
                SET status = ?, output_key = ?, error = ?, updated_at = ?
                WHERE job_id = ? AND name = ?
                """,
                (status, output_key, error, timestamp, job_id, variant_name),
            )
            connection.commit()


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
