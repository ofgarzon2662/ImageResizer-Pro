import json

from redis import Redis
from redis.exceptions import RedisError


class RedisQueueClient:
    def __init__(self, redis_url: str, queue_name: str) -> None:
        self.queue_name = queue_name
        self._client = Redis.from_url(redis_url, decode_responses=True)

    def enqueue(self, message: dict) -> None:
        self._client.rpush(self.queue_name, json.dumps(message))

    def ping(self) -> bool:
        try:
            return bool(self._client.ping())
        except RedisError:
            return False
