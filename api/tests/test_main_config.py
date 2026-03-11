import pytest

from app.main import load_settings, load_aws_settings, create_app


def test_load_settings_reads_env(monkeypatch):
    monkeypatch.setenv("MINIO_ENDPOINT", "http://storage:9000")
    monkeypatch.setenv("MINIO_PUBLIC_ENDPOINT", "http://localhost:9000")
    monkeypatch.setenv("PRESIGN_TTL_SECONDS", "1200")

    settings = load_settings()

    assert settings.minio_endpoint == "http://storage:9000"
    assert settings.minio_public_endpoint == "http://localhost:9000"
    assert settings.presign_ttl_seconds == 1200


def test_load_settings_empty_public_endpoint_becomes_none(monkeypatch):
    monkeypatch.setenv("MINIO_PUBLIC_ENDPOINT", "")

    settings = load_settings()

    assert settings.minio_public_endpoint is None


def test_load_aws_settings_reads_env(monkeypatch):
    monkeypatch.setenv("JOBS_BUCKET_INPUT", "input-bucket")
    monkeypatch.setenv("JOBS_BUCKET_OUTPUT", "output-bucket")
    monkeypatch.setenv("JOBS_QUEUE_URL", "https://sqs.example.com/queue")
    monkeypatch.setenv("JOBS_TABLE_NAME", "my-table")
    monkeypatch.setenv("AWS_REGION", "eu-west-1")
    monkeypatch.setenv("PRESIGN_TTL_SECONDS", "600")

    settings = load_aws_settings()

    assert settings.input_bucket == "input-bucket"
    assert settings.output_bucket == "output-bucket"
    assert settings.queue_url == "https://sqs.example.com/queue"
    assert settings.table_name == "my-table"
    assert settings.aws_region == "eu-west-1"
    assert settings.presign_ttl_seconds == 600


def test_load_aws_settings_missing_required_raises(monkeypatch):
    monkeypatch.delenv("JOBS_BUCKET_INPUT", raising=False)
    monkeypatch.delenv("JOBS_BUCKET_OUTPUT", raising=False)

    with pytest.raises(KeyError):
        load_aws_settings()


def test_create_app_aws_environment(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "aws")
    monkeypatch.setenv("JOBS_BUCKET_INPUT", "input-bucket")
    monkeypatch.setenv("JOBS_BUCKET_OUTPUT", "output-bucket")
    monkeypatch.setenv("JOBS_QUEUE_URL", "https://sqs.example.com/queue")
    monkeypatch.setenv("JOBS_TABLE_NAME", "my-table")

    class FakeStorage:
        def __init__(self, **kwargs):
            pass

        def presign_put(self, key, content_type, ttl_seconds):
            return ""

        def presign_get(self, key, ttl_seconds):
            return ""

        def head(self, key):
            return True

        def ping(self):
            return True

    class FakeQueue:
        def __init__(self, **kwargs):
            pass

        def enqueue(self, message):
            pass

        def ping(self):
            return True

    class FakeRepo:
        def __init__(self, **kwargs):
            pass

        def create_job(self, job_id, input_key, variants):
            pass

        def get_job(self, job_id):
            return None

        def update_status(self, job_id, status, error=None):
            return True

        def update_variant(self, job_id, variant_name, status, output_key=None, error=None):
            return True

        def ping(self):
            return True

    monkeypatch.setattr(
        "app.adapters.aws_storage_client.AWSS3StorageClient",
        lambda **kwargs: FakeStorage(),
    )
    monkeypatch.setattr(
        "app.adapters.aws_queue_client.SQSQueueClient",
        lambda **kwargs: FakeQueue(),
    )
    monkeypatch.setattr(
        "app.adapters.aws_jobs_repo.DynamoDBJobsRepository",
        lambda **kwargs: FakeRepo(),
    )

    import app.adapters.aws_storage_client as aws_storage_mod
    import app.adapters.aws_queue_client as aws_queue_mod
    import app.adapters.aws_jobs_repo as aws_jobs_mod

    monkeypatch.setattr(aws_storage_mod, "AWSS3StorageClient", lambda **kwargs: FakeStorage())
    monkeypatch.setattr(aws_queue_mod, "SQSQueueClient", lambda **kwargs: FakeQueue())
    monkeypatch.setattr(aws_jobs_mod, "DynamoDBJobsRepository", lambda **kwargs: FakeRepo())

    app = create_app()

    assert app is not None
    assert app.title == "ImageResizer-Pro API"
