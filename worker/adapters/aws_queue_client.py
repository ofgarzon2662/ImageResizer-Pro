import json
import logging
from collections.abc import Callable

import boto3

logger = logging.getLogger(__name__)


class SQSQueueConsumer:
    """SQS consumer using IAM task role credentials (no explicit keys)."""

    def __init__(
        self,
        region_name: str,
        queue_url: str,
        wait_time_seconds: int = 20,
        visibility_timeout: int = 300,
    ) -> None:
        self.queue_url = queue_url
        self.wait_time_seconds = wait_time_seconds
        self.visibility_timeout = visibility_timeout
        self._client = boto3.client("sqs", region_name=region_name)

    def consume_forever(self, handler: Callable[[dict], None]) -> None:
        while True:
            response = self._client.receive_message(
                QueueUrl=self.queue_url,
                MaxNumberOfMessages=1,
                WaitTimeSeconds=self.wait_time_seconds,
                VisibilityTimeout=self.visibility_timeout,
            )
            messages = response.get("Messages", [])
            if not messages:
                continue

            msg = messages[0]
            receipt_handle = msg["ReceiptHandle"]
            body = json.loads(msg["Body"])
            try:
                handler(body)
                self._client.delete_message(
                    QueueUrl=self.queue_url, ReceiptHandle=receipt_handle
                )
            except Exception:
                logger.exception(
                    "Failed to process message, will retry via visibility timeout"
                )
                continue

    def ping(self) -> bool:
        try:
            self._client.get_queue_attributes(
                QueueUrl=self.queue_url, AttributeNames=["QueueArn"]
            )
            return True
        except Exception:
            return False
