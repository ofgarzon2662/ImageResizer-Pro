from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.models import (
    CreateJobResponse,
    CreateUploadResponse,
    DownloadItem,
    DownloadsResponse,
    JobResponse,
    JobStatus,
    JobVariantResponse,
    VariantFormat,
    VariantStatus,
)


class FakeHealthService:
    def __init__(self) -> None:
        self.ready = True

    def is_ready(self) -> bool:
        return self.ready


class FakeUploadsService:
    def create_upload(self, _request_body):
        return CreateUploadResponse(
            upload_url="https://example.test/upload",
            input_key="uploads/2026/02/24/example.png",
            expires_in_seconds=900,
        )


class FakeJobsService:
    def create_job(self, _request_body):
        return CreateJobResponse(job_id="job-123", status=JobStatus.QUEUED)

    def get_job(self, job_id: str):
        now = datetime.now(timezone.utc)
        return JobResponse(
            job_id=job_id,
            input_key="uploads/2026/02/24/example.png",
            status=JobStatus.DONE,
            variants=[
                JobVariantResponse(
                    name="thumb",
                    width=128,
                    format=VariantFormat.JPEG,
                    status=VariantStatus.DONE,
                    output_key=f"outputs/{job_id}/thumb.jpeg",
                ),
                JobVariantResponse(
                    name="medium",
                    width=512,
                    format=VariantFormat.PNG,
                    status=VariantStatus.PENDING,
                    output_key=None,
                ),
            ],
            created_at=now,
            updated_at=now,
        )


class FakeDownloadsService:
    def get_downloads(self, job_id: str):
        return DownloadsResponse(
            job_id=job_id,
            downloads=[
                DownloadItem(
                    name="thumb",
                    output_key=f"outputs/{job_id}/thumb.jpeg",
                    download_url="https://example.test/download/thumb",
                    expires_in_seconds=900,
                )
            ],
        )


@pytest.fixture()
def client() -> TestClient:
    app = create_app()
    app.state.health_service = FakeHealthService()
    app.state.uploads_service = FakeUploadsService()
    app.state.jobs_service = FakeJobsService()
    app.state.downloads_service = FakeDownloadsService()
    return TestClient(app)
