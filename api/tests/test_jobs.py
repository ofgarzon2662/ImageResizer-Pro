from app.services.jobs_service import JobNotFoundError


def test_create_job_success(client):
    response = client.post(
        "/v1/jobs",
        json={
            "inputKey": "uploads/2026/02/24/photo.png",
            "variants": [
                {"name": "thumb", "width": 128, "format": "jpeg"},
                {"name": "medium", "width": 512, "format": "png"},
            ],
        },
    )

    assert response.status_code == 201
    assert response.json()["jobId"] == "job-123"
    assert response.json()["status"] == "QUEUED"


def test_create_job_rejects_duplicate_variant_names(client):
    response = client.post(
        "/v1/jobs",
        json={
            "inputKey": "uploads/2026/02/24/photo.png",
            "variants": [
                {"name": "thumb", "width": 128, "format": "jpeg"},
                {"name": "thumb", "width": 512, "format": "png"},
            ],
        },
    )

    assert response.status_code == 422


def test_create_job_rejects_width_out_of_bounds(client):
    response = client.post(
        "/v1/jobs",
        json={
            "inputKey": "uploads/2026/02/24/photo.png",
            "variants": [{"name": "thumb", "width": 16, "format": "jpeg"}],
        },
    )
    assert response.status_code == 422


def test_create_job_rejects_unsupported_format(client):
    response = client.post(
        "/v1/jobs",
        json={
            "inputKey": "uploads/2026/02/24/photo.png",
            "variants": [{"name": "thumb", "width": 128, "format": "gif"}],
        },
    )
    assert response.status_code == 422


def test_create_job_rejects_more_than_five_variants(client):
    variants = []
    for index in range(6):
        variants.append({"name": f"v{index}", "width": 128, "format": "jpeg"})

    response = client.post(
        "/v1/jobs",
        json={
            "inputKey": "uploads/2026/02/24/photo.png",
            "variants": variants,
        },
    )
    assert response.status_code == 422


def test_get_job_returns_status_and_variants(client):
    response = client.get("/v1/jobs/job-123")
    assert response.status_code == 200
    payload = response.json()
    assert payload["jobId"] == "job-123"
    assert payload["status"] == "DONE"
    assert len(payload["variants"]) == 2


def test_get_downloads_returns_completed_outputs(client):
    response = client.get("/v1/jobs/job-123/downloads")
    assert response.status_code == 200
    payload = response.json()
    assert payload["jobId"] == "job-123"
    assert len(payload["downloads"]) == 1
    assert payload["downloads"][0]["name"] == "thumb"
    assert "downloadUrl" in payload["downloads"][0]


def test_get_job_returns_404_when_missing(client):
    class MissingJobsService:
        def get_job(self, _job_id):
            raise JobNotFoundError()

    client.app.state.jobs_service = MissingJobsService()
    response = client.get("/v1/jobs/missing")
    assert response.status_code == 404


def test_get_downloads_returns_404_when_missing(client):
    class MissingDownloadsService:
        def get_downloads(self, _job_id):
            raise JobNotFoundError()

    client.app.state.downloads_service = MissingDownloadsService()
    response = client.get("/v1/jobs/missing/downloads")
    assert response.status_code == 404
