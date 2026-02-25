from app.adapters.queue_client import RedisQueueClient
from redis.exceptions import RedisError


class FakeRedis:
    def __init__(self):
        self.items = []
        self.should_fail = False

    def rpush(self, queue_name, payload):
        self.items.append((queue_name, payload))

    def ping(self):
        if self.should_fail:
            raise RedisError("redis down")
        return True


def test_queue_client_enqueue(monkeypatch):
    fake_redis = FakeRedis()

    class FakeRedisClass:
        @staticmethod
        def from_url(_redis_url, decode_responses):
            assert decode_responses
            return fake_redis

    monkeypatch.setattr("app.adapters.queue_client.Redis", FakeRedisClass)
    client = RedisQueueClient("redis://redis:6379/0", "image_jobs")
    client.enqueue({"jobId": "job-1"})

    assert len(fake_redis.items) == 1
    assert fake_redis.items[0][0] == "image_jobs"


def test_queue_client_ping_handles_errors(monkeypatch):
    fake_redis = FakeRedis()

    class FakeRedisClass:
        @staticmethod
        def from_url(_redis_url, decode_responses):
            return fake_redis

    monkeypatch.setattr("app.adapters.queue_client.Redis", FakeRedisClass)
    client = RedisQueueClient("redis://redis:6379/0", "image_jobs")
    assert client.ping()
    fake_redis.should_fail = True
    assert not client.ping()
