import pytest

from app.adapters.aws_jobs_repo import DynamoDBJobsRepository
from app.models import JobStatus, VariantStatus


class FakeConditionalCheckFailed(Exception):
    pass


class FakeDynamoDBClient:
    class exceptions:
        ConditionalCheckFailedException = FakeConditionalCheckFailed

    def __init__(self):
        self.calls = {}
        self._items = {}
        self._fail_put = False
        self._fail_update = False
        self._fail_describe = False

    def put_item(self, **kwargs):
        if self._fail_put:
            raise self.exceptions.ConditionalCheckFailedException("duplicate")
        key = kwargs["Item"]["jobId"]["S"]
        self._items[key] = kwargs["Item"]
        self.calls.setdefault("put_item", []).append(kwargs)

    def get_item(self, **kwargs):
        key = kwargs["Key"]["jobId"]["S"]
        item = self._items.get(key)
        self.calls.setdefault("get_item", []).append(kwargs)
        if item is None:
            return {}
        return {"Item": item}

    def update_item(self, **kwargs):
        if self._fail_update:
            raise self.exceptions.ConditionalCheckFailedException("not found")
        self.calls.setdefault("update_item", []).append(kwargs)

    def describe_table(self, **kwargs):
        if self._fail_describe:
            raise RuntimeError("table not found")
        self.calls.setdefault("describe_table", []).append(kwargs)


def _make_repo(monkeypatch) -> tuple[DynamoDBJobsRepository, FakeDynamoDBClient]:
    fake_client = FakeDynamoDBClient()

    def fake_factory(_service, region_name):
        return fake_client

    monkeypatch.setattr("app.adapters.aws_jobs_repo.boto3.client", fake_factory)
    repo = DynamoDBJobsRepository(region_name="us-east-1", table_name="test-jobs")
    return repo, fake_client


def test_create_job_happy_path(monkeypatch):
    repo, fake = _make_repo(monkeypatch)
    variants = [{"name": "thumb", "width": 200, "format": "webp"}]

    repo.create_job("job-1", "uploads/input.jpg", variants)

    assert len(fake.calls["put_item"]) == 1
    item = fake.calls["put_item"][0]["Item"]
    assert item["jobId"]["S"] == "job-1"
    assert item["inputKey"]["S"] == "uploads/input.jpg"
    assert item["status"]["S"] == "CREATED"
    assert len(item["variants"]["L"]) == 1
    assert item["variants"]["L"][0]["M"]["name"]["S"] == "thumb"


def test_create_job_duplicate_raises_value_error(monkeypatch):
    repo, fake = _make_repo(monkeypatch)
    fake._fail_put = True

    with pytest.raises(ValueError, match="Job job-1 already exists"):
        repo.create_job("job-1", "uploads/input.jpg", [])


def test_get_job_found(monkeypatch):
    repo, fake = _make_repo(monkeypatch)
    fake._items["job-1"] = {
        "jobId": {"S": "job-1"},
        "inputKey": {"S": "uploads/input.jpg"},
        "status": {"S": "CREATED"},
        "error": {"NULL": True},
        "createdAt": {"S": "2026-01-01T00:00:00+00:00"},
        "updatedAt": {"S": "2026-01-01T00:00:00+00:00"},
        "variants": {
            "L": [
                {
                    "M": {
                        "name": {"S": "thumb"},
                        "width": {"N": "200"},
                        "format": {"S": "webp"},
                        "status": {"S": "PENDING"},
                        "outputKey": {"NULL": True},
                        "error": {"NULL": True},
                    }
                }
            ]
        },
    }

    result = repo.get_job("job-1")

    assert result is not None
    assert result["job_id"] == "job-1"
    assert result["input_key"] == "uploads/input.jpg"
    assert result["status"] == "CREATED"
    assert result["error"] is None
    assert len(result["variants"]) == 1
    assert result["variants"][0]["name"] == "thumb"
    assert result["variants"][0]["width"] == 200
    assert result["variants"][0]["output_key"] is None


def test_get_job_not_found(monkeypatch):
    repo, _ = _make_repo(monkeypatch)

    result = repo.get_job("nonexistent")

    assert result is None


def test_update_status_success(monkeypatch):
    repo, fake = _make_repo(monkeypatch)

    result = repo.update_status("job-1", JobStatus.RUNNING)

    assert result is True
    assert len(fake.calls["update_item"]) == 1
    call = fake.calls["update_item"][0]
    assert call["ExpressionAttributeValues"][":s"]["S"] == "RUNNING"
    assert ":e" in call["ExpressionAttributeValues"]


def test_update_status_with_error(monkeypatch):
    repo, fake = _make_repo(monkeypatch)

    result = repo.update_status("job-1", JobStatus.FAILED, error="boom")

    assert result is True
    call = fake.calls["update_item"][0]
    assert call["ExpressionAttributeValues"][":e"]["S"] == "boom"


def test_update_status_not_found(monkeypatch):
    repo, fake = _make_repo(monkeypatch)
    fake._fail_update = True

    result = repo.update_status("no-job", JobStatus.RUNNING)

    assert result is False


def test_update_variant_success(monkeypatch):
    repo, fake = _make_repo(monkeypatch)
    fake._items["job-1"] = {
        "variants": {
            "L": [
                {"M": {"name": {"S": "thumb"}}},
                {"M": {"name": {"S": "medium"}}},
            ]
        }
    }

    result = repo.update_variant("job-1", "medium", VariantStatus.DONE, output_key="outputs/job-1/medium.png")

    assert result is True
    call = fake.calls["update_item"][0]
    assert "variants[1]" in call["UpdateExpression"]
    assert call["ExpressionAttributeValues"][":s"]["S"] == "DONE"
    assert call["ExpressionAttributeValues"][":o"]["S"] == "outputs/job-1/medium.png"


def test_update_variant_with_error(monkeypatch):
    repo, fake = _make_repo(monkeypatch)
    fake._items["job-1"] = {
        "variants": {"L": [{"M": {"name": {"S": "thumb"}}}]}
    }

    result = repo.update_variant("job-1", "thumb", VariantStatus.FAILED, error="resize failed")

    assert result is True
    call = fake.calls["update_item"][0]
    assert call["ExpressionAttributeValues"][":e"]["S"] == "resize failed"


def test_update_variant_job_not_found(monkeypatch):
    repo, _ = _make_repo(monkeypatch)

    result = repo.update_variant("no-job", "thumb", VariantStatus.DONE)

    assert result is False


def test_update_variant_name_not_found(monkeypatch):
    repo, fake = _make_repo(monkeypatch)
    fake._items["job-1"] = {
        "variants": {"L": [{"M": {"name": {"S": "thumb"}}}]}
    }

    result = repo.update_variant("job-1", "nonexistent", VariantStatus.DONE)

    assert result is False


def test_ping_success(monkeypatch):
    repo, _ = _make_repo(monkeypatch)

    assert repo.ping() is True


def test_ping_failure(monkeypatch):
    repo, fake = _make_repo(monkeypatch)
    fake._fail_describe = True

    assert repo.ping() is False
