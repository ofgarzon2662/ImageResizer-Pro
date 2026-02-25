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
