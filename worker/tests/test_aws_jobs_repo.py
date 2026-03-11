from adapters.aws_jobs_repo import DynamoDBJobsRepository


class FakeDynamoDBClient:
    def __init__(self):
        self.calls = {}
        self._items = {}

    def update_item(self, **kwargs):
        self.calls.setdefault("update_item", []).append(kwargs)

    def get_item(self, **kwargs):
        key = kwargs["Key"]["jobId"]["S"]
        item = self._items.get(key)
        self.calls.setdefault("get_item", []).append(kwargs)
        if item is None:
            return {}
        return {"Item": item}


def _make_repo(monkeypatch) -> tuple[DynamoDBJobsRepository, FakeDynamoDBClient]:
    fake = FakeDynamoDBClient()

    def fake_factory(_service, region_name):
        return fake

    monkeypatch.setattr("adapters.aws_jobs_repo.boto3.client", fake_factory)
    repo = DynamoDBJobsRepository(region_name="us-east-1", table_name="test-jobs")
    return repo, fake


def test_update_job_status_without_error(monkeypatch):
    repo, fake = _make_repo(monkeypatch)

    repo.update_job_status("job-1", "RUNNING")

    assert len(fake.calls["update_item"]) == 1
    call = fake.calls["update_item"][0]
    assert call["Key"]["jobId"]["S"] == "job-1"
    assert call["ExpressionAttributeValues"][":s"]["S"] == "RUNNING"
    assert "NULL" in call["ExpressionAttributeValues"][":e"]


def test_update_job_status_with_error(monkeypatch):
    repo, fake = _make_repo(monkeypatch)

    repo.update_job_status("job-1", "FAILED", error="something broke")

    call = fake.calls["update_item"][0]
    assert call["ExpressionAttributeValues"][":s"]["S"] == "FAILED"
    assert call["ExpressionAttributeValues"][":e"]["S"] == "something broke"


def test_update_variant_status_success(monkeypatch):
    repo, fake = _make_repo(monkeypatch)
    fake._items["job-1"] = {
        "variants": {
            "L": [
                {"M": {"name": {"S": "thumb"}}},
                {"M": {"name": {"S": "medium"}}},
            ]
        }
    }

    repo.update_variant_status(
        "job-1", "medium", "DONE", output_key="outputs/job-1/medium.png"
    )

    assert len(fake.calls["update_item"]) == 1
    call = fake.calls["update_item"][0]
    assert "variants[1]" in call["UpdateExpression"]
    assert call["ExpressionAttributeValues"][":s"]["S"] == "DONE"
    assert call["ExpressionAttributeValues"][":o"]["S"] == "outputs/job-1/medium.png"


def test_update_variant_status_with_error(monkeypatch):
    repo, fake = _make_repo(monkeypatch)
    fake._items["job-1"] = {
        "variants": {"L": [{"M": {"name": {"S": "thumb"}}}]}
    }

    repo.update_variant_status("job-1", "thumb", "FAILED", error="resize failed")

    call = fake.calls["update_item"][0]
    assert call["ExpressionAttributeValues"][":e"]["S"] == "resize failed"


def test_update_variant_status_job_not_found(monkeypatch):
    repo, _ = _make_repo(monkeypatch)

    repo.update_variant_status("no-job", "thumb", "DONE")


def test_update_variant_status_variant_not_found(monkeypatch):
    repo, fake = _make_repo(monkeypatch)
    fake._items["job-1"] = {
        "variants": {"L": [{"M": {"name": {"S": "thumb"}}}]}
    }

    repo.update_variant_status("job-1", "nonexistent", "DONE")

    assert "update_item" not in fake.calls
