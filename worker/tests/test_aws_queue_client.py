import json

from adapters.aws_queue_client import SQSQueueConsumer


class StopLoop(Exception):
    pass


class FakeSQSClient:
    def __init__(self):
        self.calls = {}
        self._messages = []
        self._receive_count = 0
        self._fail_get_attrs = False

    def receive_message(self, **kwargs):
        self._receive_count += 1
        self.calls.setdefault("receive_message", []).append(kwargs)
        if self._messages:
            return {"Messages": [self._messages.pop(0)]}
        raise StopLoop("no more messages")

    def delete_message(self, **kwargs):
        self.calls.setdefault("delete_message", []).append(kwargs)

    def get_queue_attributes(self, **kwargs):
        if self._fail_get_attrs:
            raise RuntimeError("queue not found")
        self.calls.setdefault("get_queue_attributes", []).append(kwargs)


def _make_consumer(monkeypatch) -> tuple[SQSQueueConsumer, FakeSQSClient]:
    fake = FakeSQSClient()

    def fake_factory(_service, region_name):
        return fake

    monkeypatch.setattr("adapters.aws_queue_client.boto3.client", fake_factory)
    consumer = SQSQueueConsumer(
        region_name="us-east-1",
        queue_url="https://sqs.example.com/queue",
    )
    return consumer, fake


def test_consume_forever_processes_and_deletes(monkeypatch):
    consumer, fake = _make_consumer(monkeypatch)
    body = {"jobId": "job-1", "inputKey": "uploads/key.jpg", "variants": []}
    fake._messages.append({
        "ReceiptHandle": "receipt-1",
        "Body": json.dumps(body),
    })
    seen = []

    try:
        consumer.consume_forever(lambda msg: seen.append(msg))
    except StopLoop:
        pass

    assert len(seen) == 1
    assert seen[0]["jobId"] == "job-1"
    assert len(fake.calls["delete_message"]) == 1
    assert fake.calls["delete_message"][0]["ReceiptHandle"] == "receipt-1"


def test_consume_forever_handler_error_continues(monkeypatch):
    consumer, fake = _make_consumer(monkeypatch)
    fake._messages.append({
        "ReceiptHandle": "receipt-err",
        "Body": json.dumps({"jobId": "job-bad"}),
    })

    def failing_handler(msg):
        raise ValueError("handler error")

    try:
        consumer.consume_forever(failing_handler)
    except StopLoop:
        pass

    assert "delete_message" not in fake.calls


def test_consume_forever_skips_empty_messages(monkeypatch):
    consumer, fake = _make_consumer(monkeypatch)
    call_count = [0]
    original_receive = fake.receive_message

    def patched_receive(**kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            return {"Messages": []}
        if call_count[0] == 2:
            return {
                "Messages": [
                    {
                        "ReceiptHandle": "r-2",
                        "Body": json.dumps({"jobId": "job-2"}),
                    }
                ]
            }
        raise StopLoop("done")

    fake.receive_message = patched_receive
    seen = []

    try:
        consumer.consume_forever(lambda msg: seen.append(msg))
    except StopLoop:
        pass

    assert len(seen) == 1
    assert seen[0]["jobId"] == "job-2"


def test_ping_success(monkeypatch):
    consumer, _ = _make_consumer(monkeypatch)

    assert consumer.ping() is True


def test_ping_failure(monkeypatch):
    consumer, fake = _make_consumer(monkeypatch)
    fake._fail_get_attrs = True

    assert consumer.ping() is False
