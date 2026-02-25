import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.models import JobStatus, VariantStatus


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

    def create_job(self, job_id: str, input_key: str, variants: list[dict[str, Any]]) -> None:
        timestamp = _utc_now_iso()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO jobs (job_id, input_key, status, error, created_at, updated_at)
                VALUES (?, ?, ?, NULL, ?, ?)
                """,
                (job_id, input_key, JobStatus.CREATED.value, timestamp, timestamp),
            )
            for variant in variants:
                connection.execute(
                    """
                    INSERT INTO job_variants
                    (job_id, name, width, format, status, output_key, error, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, NULL, NULL, ?, ?)
                    """,
                    (
                        job_id,
                        variant["name"],
                        variant["width"],
                        variant["format"],
                        VariantStatus.PENDING.value,
                        timestamp,
                        timestamp,
                    ),
                )
            connection.commit()

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            job_row = connection.execute(
                """
                SELECT job_id, input_key, status, error, created_at, updated_at
                FROM jobs
                WHERE job_id = ?
                """,
                (job_id,),
            ).fetchone()
            if job_row is None:
                return None

            variant_rows = connection.execute(
                """
                SELECT name, width, format, status, output_key, error
                FROM job_variants
                WHERE job_id = ?
                ORDER BY id ASC
                """,
                (job_id,),
            ).fetchall()

        return {
            "job_id": job_row["job_id"],
            "input_key": job_row["input_key"],
            "status": job_row["status"],
            "error": job_row["error"],
            "created_at": job_row["created_at"],
            "updated_at": job_row["updated_at"],
            "variants": [
                {
                    "name": row["name"],
                    "width": row["width"],
                    "format": row["format"],
                    "status": row["status"],
                    "output_key": row["output_key"],
                    "error": row["error"],
                }
                for row in variant_rows
            ],
        }

    def update_status(self, job_id: str, status: JobStatus, error: str | None = None) -> bool:
        timestamp = _utc_now_iso()
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE jobs
                SET status = ?, error = ?, updated_at = ?
                WHERE job_id = ?
                """,
                (status.value, error, timestamp, job_id),
            )
            connection.commit()
            return cursor.rowcount > 0

    def update_variant(
        self,
        job_id: str,
        variant_name: str,
        status: VariantStatus,
        output_key: str | None = None,
        error: str | None = None,
    ) -> bool:
        timestamp = _utc_now_iso()
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE job_variants
                SET status = ?, output_key = ?, error = ?, updated_at = ?
                WHERE job_id = ? AND name = ?
                """,
                (status.value, output_key, error, timestamp, job_id, variant_name),
            )
            connection.commit()
            return cursor.rowcount > 0

    def ping(self) -> bool:
        try:
            with self._connect() as connection:
                connection.execute("SELECT 1")
            return True
        except sqlite3.Error:
            return False


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
