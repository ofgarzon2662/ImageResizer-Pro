import pytest

import worker


def test_load_settings_from_environment(monkeypatch):
    monkeypatch.setenv("MINIO_ENDPOINT", "http://storage:9000")
    monkeypatch.setenv("MINIO_ACCESS_KEY", "key")
    monkeypatch.setenv("MINIO_SECRET_KEY", "secret")
    monkeypatch.setenv("MINIO_REGION", "eu-west-1")
    monkeypatch.setenv("MINIO_BUCKET", "bucket")
    monkeypatch.setenv("REDIS_URL", "redis://example:6379/0")
    monkeypatch.setenv("REDIS_QUEUE_NAME", "jobs")
    monkeypatch.setenv("SQLITE_PATH", "/tmp/jobs.db")
    monkeypatch.setenv("WORKER_METRICS_PORT", "9300")

    settings = worker.load_settings()

    assert settings.minio_endpoint == "http://storage:9000"
    assert settings.minio_bucket == "bucket"
    assert settings.redis_queue_name == "jobs"
    assert settings.metrics_port == 9300


def test_main_wires_components_and_consumes(monkeypatch):
    calls = {"sleep": 0, "metrics": 0, "consumed": 0}

    class FakeQueue:
        def __init__(self, _url, _name):
            self.ping_calls = 0

        def ping(self):
            self.ping_calls += 1
            return self.ping_calls > 1

        def consume_forever(self, handler):
            calls["consumed"] += 1
            handler({"jobId": "job-1", "inputKey": "uploads/key.jpg", "variants": []})
            raise RuntimeError("stop")

    class FakeStorage:
        def __init__(self, **_kwargs):
            pass

    class FakeRepo:
        def __init__(self, _path):
            pass

    class FakeImage:
        pass

    class FakeProcessor:
        def __init__(self, **_kwargs):
            pass

        def process(self, _message):
            return None

    monkeypatch.setattr(worker, "RedisQueueConsumer", FakeQueue)
    monkeypatch.setattr(worker, "S3StorageClient", FakeStorage)
    monkeypatch.setattr(worker, "SQLiteJobsRepository", FakeRepo)
    monkeypatch.setattr(worker, "ImageProcessor", FakeImage)
    monkeypatch.setattr(worker, "JobProcessor", FakeProcessor)
    monkeypatch.setattr(worker, "start_metrics_server", lambda _port: calls.__setitem__("metrics", 1))
    monkeypatch.setattr(worker.time, "sleep", lambda _seconds: calls.__setitem__("sleep", calls["sleep"] + 1))

    with pytest.raises(RuntimeError):
        worker.main()

    assert calls["metrics"] == 1
    assert calls["sleep"] == 1
    assert calls["consumed"] == 1


def test_load_aws_settings_reads_env(monkeypatch):
    monkeypatch.setenv("JOBS_BUCKET_INPUT", "input-bucket")
    monkeypatch.setenv("JOBS_BUCKET_OUTPUT", "output-bucket")
    monkeypatch.setenv("JOBS_QUEUE_URL", "https://sqs.example.com/queue")
    monkeypatch.setenv("JOBS_TABLE_NAME", "my-table")
    monkeypatch.setenv("AWS_REGION", "eu-west-1")
    monkeypatch.setenv("WORKER_METRICS_PORT", "9200")

    settings = worker.load_aws_settings()

    assert settings.input_bucket == "input-bucket"
    assert settings.output_bucket == "output-bucket"
    assert settings.queue_url == "https://sqs.example.com/queue"
    assert settings.table_name == "my-table"
    assert settings.aws_region == "eu-west-1"
    assert settings.metrics_port == 9200


def test_load_aws_settings_missing_required_raises(monkeypatch):
    monkeypatch.delenv("JOBS_BUCKET_INPUT", raising=False)
    monkeypatch.delenv("JOBS_BUCKET_OUTPUT", raising=False)

    with pytest.raises(KeyError):
        worker.load_aws_settings()


def test_main_aws_environment(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "aws")
    monkeypatch.setenv("JOBS_BUCKET_INPUT", "input-bucket")
    monkeypatch.setenv("JOBS_BUCKET_OUTPUT", "output-bucket")
    monkeypatch.setenv("JOBS_QUEUE_URL", "https://sqs.example.com/queue")
    monkeypatch.setenv("JOBS_TABLE_NAME", "my-table")

    calls = {"metrics": 0, "consumed": 0}

    class FakeAWSQueue:
        def __init__(self, region_name, queue_url):
            self.ping_count = 0

        def ping(self):
            self.ping_count += 1
            return True

        def consume_forever(self, handler):
            calls["consumed"] += 1
            raise RuntimeError("stop")

    class FakeAWSStorage:
        def __init__(self, region_name, input_bucket, output_bucket):
            pass

    class FakeAWSRepo:
        def __init__(self, region_name, table_name):
            pass

    class FakeImage:
        pass

    class FakeProcessor:
        def __init__(self, **_kwargs):
            pass

        def process(self, _message):
            return None

    import adapters.aws_queue_client as aws_queue_mod
    import adapters.aws_storage_client as aws_storage_mod
    import adapters.aws_jobs_repo as aws_jobs_mod

    monkeypatch.setattr(aws_queue_mod, "SQSQueueConsumer", FakeAWSQueue)
    monkeypatch.setattr(aws_storage_mod, "AWSS3StorageClient", FakeAWSStorage)
    monkeypatch.setattr(aws_jobs_mod, "DynamoDBJobsRepository", FakeAWSRepo)
    monkeypatch.setattr(worker, "ImageProcessor", FakeImage)
    monkeypatch.setattr(worker, "JobProcessor", FakeProcessor)
    monkeypatch.setattr(worker, "start_metrics_server", lambda _port: calls.__setitem__("metrics", 1))

    with pytest.raises(RuntimeError):
        worker.main()

    assert calls["metrics"] == 1
    assert calls["consumed"] == 1
