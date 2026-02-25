import json
from collections.abc import Callable

from redis import Redis
from redis.exceptions import RedisError


class RedisQueueConsumer:
    def __init__(self, redis_url: str, queue_name: str) -> None:
        self.queue_name = queue_name
        self._client = Redis.from_url(redis_url, decode_responses=True)

    def consume_forever(self, handler: Callable[[dict], None]) -> None:
        while True:
            item = self._client.blpop(self.queue_name, timeout=1)
            if item is None:
                continue
            _, payload = item
            message = json.loads(payload)
            try:
                handler(message)
            except Exception:
                # The processor persists failure state, so the consumer can continue.
                continue

    def ping(self) -> bool:
        try:
            return bool(self._client.ping())
        except RedisError:
            return False
