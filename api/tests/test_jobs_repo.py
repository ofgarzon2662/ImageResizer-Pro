from app.adapters.jobs_repo import SQLiteJobsRepository
from app.models import JobStatus, VariantStatus


def test_jobs_repo_create_and_get_job(tmp_path):
    db_path = tmp_path / "jobs.db"
    repo = SQLiteJobsRepository(str(db_path))

    repo.create_job(
        job_id="job-1",
        input_key="uploads/2026/02/25/input.jpg",
        variants=[
            {"name": "thumb", "width": 200, "format": "webp"},
            {"name": "medium", "width": 800, "format": "jpeg"},
        ],
    )

    record = repo.get_job("job-1")
    assert record is not None
    assert record["status"] == "CREATED"
    assert len(record["variants"]) == 2


def test_jobs_repo_update_status_and_variant(tmp_path):
    db_path = tmp_path / "jobs.db"
    repo = SQLiteJobsRepository(str(db_path))
    repo.create_job(
        job_id="job-2",
        input_key="uploads/2026/02/25/input.jpg",
        variants=[{"name": "thumb", "width": 200, "format": "webp"}],
    )

    assert repo.update_status("job-2", JobStatus.RUNNING)
    assert repo.update_variant(
        "job-2",
        "thumb",
        VariantStatus.DONE,
        output_key="outputs/job-2/thumb.webp",
    )

    record = repo.get_job("job-2")
    assert record["status"] == "RUNNING"
    assert record["variants"][0]["status"] == "DONE"
    assert record["variants"][0]["output_key"] == "outputs/job-2/thumb.webp"


def test_jobs_repo_ping(tmp_path):
    repo = SQLiteJobsRepository(str(tmp_path / "jobs.db"))
    assert repo.ping()
