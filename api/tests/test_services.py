import pytest

from app.models import CreateJobRequest, CreateUploadRequest
from app.services.downloads_service import DownloadsService
from app.services.jobs_service import JobNotFoundError, JobsService
from app.services.uploads_service import UploadsService


class FakeStorage:
    def __init__(self, input_exists=True):
        self.input_exists = input_exists
        self.put_calls = []
        self.get_calls = []

    def presign_put(self, key, content_type, ttl_seconds):
        self.put_calls.append((key, content_type, ttl_seconds))
        return f"http://signed-put/{key}"

    def presign_get(self, key, ttl_seconds):
        self.get_calls.append((key, ttl_seconds))
        return f"http://signed-get/{key}"

    def head(self, _key):
        return self.input_exists


class FakeQueue:
    def __init__(self):
        self.messages = []

    def enqueue(self, message):
        self.messages.append(message)


class FakeRepo:
    def __init__(self, record=None):
        self.created = []
        self.status_updates = []
        self.record = record

    def create_job(self, job_id, input_key, variants):
        self.created.append((job_id, input_key, variants))

    def update_status(self, job_id, status, error=None):
        self.status_updates.append((job_id, status.value, error))
        return True

    def get_job(self, _job_id):
        return self.record


def test_uploads_service_returns_presigned_url_and_key():
    storage = FakeStorage()
    service = UploadsService(storage_client=storage, presign_ttl_seconds=600)
    response = service.create_upload(
        CreateUploadRequest(filename="photo.png", contentType="image/png")
    )

    assert response.upload_url.startswith("http://signed-put/uploads/")
    assert response.input_key.startswith("uploads/")
    assert response.expires_in_seconds == 600
    assert len(storage.put_calls) == 1


def test_jobs_service_create_job_enqueues_message():
    storage = FakeStorage(input_exists=True)
    queue = FakeQueue()
    repo = FakeRepo()
    service = JobsService(jobs_repo=repo, queue_client=queue, storage_client=storage)
    request = CreateJobRequest(
        inputKey="uploads/2026/02/25/input.jpg",
        variants=[
            {"name": "thumb", "width": 200, "format": "webp"},
            {"name": "medium", "width": 800, "format": "jpeg"},
        ],
    )

    response = service.create_job(request)

    assert response.job_id
    assert response.status.value == "QUEUED"
    assert len(repo.created) == 1
    assert len(queue.messages) == 1
    assert queue.messages[0]["inputKey"] == "uploads/2026/02/25/input.jpg"


def test_jobs_service_rejects_non_upload_input_key():
    service = JobsService(jobs_repo=FakeRepo(), queue_client=FakeQueue(), storage_client=FakeStorage())
    request = CreateJobRequest(
        inputKey="not-uploads/input.jpg",
        variants=[{"name": "thumb", "width": 200, "format": "webp"}],
    )

    with pytest.raises(ValueError):
        service.create_job(request)


def test_jobs_service_rejects_missing_storage_input():
    service = JobsService(
        jobs_repo=FakeRepo(),
        queue_client=FakeQueue(),
        storage_client=FakeStorage(input_exists=False),
    )
    request = CreateJobRequest(
        inputKey="uploads/2026/02/25/input.jpg",
        variants=[{"name": "thumb", "width": 200, "format": "webp"}],
    )

    with pytest.raises(ValueError):
        service.create_job(request)


def test_jobs_service_get_job_raises_not_found():
    service = JobsService(jobs_repo=FakeRepo(record=None), queue_client=FakeQueue(), storage_client=FakeStorage())
    with pytest.raises(JobNotFoundError):
        service.get_job("missing")


def test_downloads_service_returns_only_done_variants():
    repo = FakeRepo(
        record={
            "job_id": "job-1",
            "input_key": "uploads/2026/02/25/input.jpg",
            "status": "DONE",
            "error": None,
            "created_at": "2026-02-25T00:00:00Z",
            "updated_at": "2026-02-25T00:00:01Z",
            "variants": [
                {
                    "name": "thumb",
                    "width": 200,
                    "format": "webp",
                    "status": "DONE",
                    "output_key": "outputs/job-1/thumb.webp",
                    "error": None,
                },
                {
                    "name": "medium",
                    "width": 800,
                    "format": "jpeg",
                    "status": "FAILED",
                    "output_key": None,
                    "error": "error",
                },
            ],
        }
    )
    storage = FakeStorage()
    service = DownloadsService(jobs_repo=repo, storage_client=storage, presign_ttl_seconds=900)

    response = service.get_downloads("job-1")

    assert response.job_id == "job-1"
    assert len(response.downloads) == 1
    assert response.downloads[0].name == "thumb"
    assert len(storage.get_calls) == 1


def test_downloads_service_raises_when_job_missing():
    service = DownloadsService(jobs_repo=FakeRepo(record=None), storage_client=FakeStorage(), presign_ttl_seconds=900)
    with pytest.raises(JobNotFoundError):
        service.get_downloads("missing")
