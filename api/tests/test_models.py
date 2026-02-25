import pytest
from pydantic import ValidationError

from app.models import CreateJobRequest


def test_create_job_request_rejects_duplicate_variant_names():
    with pytest.raises(ValidationError):
        CreateJobRequest(
            inputKey="uploads/2026/02/25/input.jpg",
            variants=[
                {"name": "thumb", "width": 200, "format": "jpeg"},
                {"name": "thumb", "width": 800, "format": "png"},
            ],
        )


def test_create_job_request_accepts_distinct_variant_names():
    request = CreateJobRequest(
        inputKey="uploads/2026/02/25/input.jpg",
        variants=[
            {"name": "thumb", "width": 200, "format": "webp"},
            {"name": "medium", "width": 800, "format": "jpeg"},
        ],
    )
    assert request.input_key.startswith("uploads/")
    assert len(request.variants) == 2
