import json

from adapters.queue_client import RedisQueueConsumer
from redis.exceptions import RedisError


class StopConsumption(Exception):
    pass


class FakeRedis:
    def __init__(self):
        self.items = [
            ("image_jobs", json.dumps({"jobId": "job-1", "inputKey": "uploads/key.jpg", "variants": []}))
        ]
        self.fail_ping = False

    def blpop(self, _queue_name, timeout):
        if self.items:
            return self.items.pop(0)
        raise StopConsumption()

    def ping(self):
        if self.fail_ping:
            raise RedisError("redis down")
        return True


def test_queue_consumer_consumes_message(monkeypatch):
    fake_redis = FakeRedis()
    seen = []

    class FakeRedisClass:
        @staticmethod
        def from_url(_url, decode_responses):
            assert decode_responses
            return fake_redis

    monkeypatch.setattr("adapters.queue_client.Redis", FakeRedisClass)
    consumer = RedisQueueConsumer("redis://redis:6379/0", "image_jobs")

    try:
        consumer.consume_forever(lambda message: seen.append(message))
    except StopConsumption:
        pass

    assert len(seen) == 1
    assert seen[0]["jobId"] == "job-1"


def test_queue_consumer_ping_handles_errors(monkeypatch):
    fake_redis = FakeRedis()

    class FakeRedisClass:
        @staticmethod
        def from_url(_url, decode_responses):
            return fake_redis

    monkeypatch.setattr("adapters.queue_client.Redis", FakeRedisClass)
    consumer = RedisQueueConsumer("redis://redis:6379/0", "image_jobs")
    assert consumer.ping()
    fake_redis.fail_ping = True
    assert not consumer.ping()
