from processor import JobProcessor


class FakeJobsRepo:
    def __init__(self) -> None:
        self.job_status_updates = []
        self.variant_updates = []

    def update_job_status(self, job_id, status, error=None):
        self.job_status_updates.append((job_id, status, error))

    def update_variant_status(self, job_id, name, status, output_key=None, error=None):
        self.variant_updates.append((job_id, name, status, output_key, error))


class FakeStorageClient:
    def __init__(self, should_fail=False) -> None:
        self.should_fail = should_fail
        self.uploaded = []

    def download_bytes(self, _key):
        return b"source-bytes"

    def upload_bytes(self, key, content_type, payload):
        if self.should_fail:
            raise RuntimeError("upload failed")
        self.uploaded.append((key, content_type, payload))


class FakeImageProcessor:
    def create_variant(self, image_bytes, width, output_format):
        return f"{len(image_bytes)}-{width}-{output_format}".encode()


def test_processor_sets_running_and_done_states():
    repo = FakeJobsRepo()
    storage = FakeStorageClient()
    image = FakeImageProcessor()
    processor = JobProcessor(repo, storage, image)
    message = {
        "jobId": "job-1",
        "inputKey": "uploads/2026/02/24/source.png",
        "variants": [
            {"name": "thumb", "width": 128, "format": "jpeg"},
            {"name": "medium", "width": 512, "format": "png"},
        ],
    }

    processor.process(message)

    assert repo.job_status_updates[0][1] == "RUNNING"
    assert repo.job_status_updates[-1][1] == "DONE"
    assert len(storage.uploaded) == 2
    assert any(update[2] == "DONE" for update in repo.variant_updates)


def test_processor_marks_job_failed_on_error():
    repo = FakeJobsRepo()
    storage = FakeStorageClient(should_fail=True)
    image = FakeImageProcessor()
    processor = JobProcessor(repo, storage, image)
    message = {
        "jobId": "job-2",
        "inputKey": "uploads/2026/02/24/source.png",
        "variants": [{"name": "thumb", "width": 128, "format": "jpeg"}],
    }

    try:
        processor.process(message)
    except RuntimeError:
        pass

    assert repo.job_status_updates[-1][1] == "FAILED"
