import sqlite3

from adapters.jobs_repo import SQLiteJobsRepository


def _seed_job(repo: SQLiteJobsRepository, job_id: str) -> None:
    with sqlite3.connect(repo.db_path) as connection:
        connection.execute(
            """
            INSERT INTO jobs (job_id, input_key, status, error, created_at, updated_at)
            VALUES (?, ?, ?, NULL, datetime('now'), datetime('now'))
            """,
            (job_id, "uploads/2026/02/25/input.jpg", "QUEUED"),
        )
        connection.execute(
            """
            INSERT INTO job_variants
            (job_id, name, width, format, status, output_key, error, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, NULL, NULL, datetime('now'), datetime('now'))
            """,
            (job_id, "thumb", 200, "webp", "PENDING"),
        )
        connection.commit()


def test_worker_jobs_repo_updates_job_and_variant(tmp_path):
    repo = SQLiteJobsRepository(str(tmp_path / "jobs.db"))
    _seed_job(repo, "job-1")

    repo.update_job_status("job-1", "RUNNING")
    repo.update_variant_status("job-1", "thumb", "DONE", output_key="outputs/job-1/thumb.webp")

    with sqlite3.connect(repo.db_path) as connection:
        job_status = connection.execute(
            "SELECT status FROM jobs WHERE job_id = ?",
            ("job-1",),
        ).fetchone()[0]
        variant_row = connection.execute(
            "SELECT status, output_key FROM job_variants WHERE job_id = ? AND name = ?",
            ("job-1", "thumb"),
        ).fetchone()

    assert job_status == "RUNNING"
    assert variant_row[0] == "DONE"
    assert variant_row[1] == "outputs/job-1/thumb.webp"
