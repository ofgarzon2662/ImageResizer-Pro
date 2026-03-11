import json

import boto3


class SQSQueueClient:
    """SQS queue client that relies on IAM task role credentials (no explicit keys)."""

    def __init__(self, region_name: str, queue_url: str) -> None:
        self.queue_url = queue_url
        self._client = boto3.client("sqs", region_name=region_name)

    def enqueue(self, message: dict) -> None:
        self._client.send_message(
            QueueUrl=self.queue_url,
            MessageBody=json.dumps(message),
        )

    def ping(self) -> bool:
        try:
            self._client.get_queue_attributes(
                QueueUrl=self.queue_url,
                AttributeNames=["QueueArn"],
            )
            return True
        except Exception:
            return False
