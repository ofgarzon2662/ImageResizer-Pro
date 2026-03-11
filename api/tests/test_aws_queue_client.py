import json

from app.adapters.aws_queue_client import SQSQueueClient


class FakeSQSClient:
    def __init__(self):
        self.calls = {}
        self._fail_get_attrs = False

    def send_message(self, **kwargs):
        self.calls.setdefault("send_message", []).append(kwargs)

    def get_queue_attributes(self, **kwargs):
        if self._fail_get_attrs:
            raise RuntimeError("queue not found")
        self.calls.setdefault("get_queue_attributes", []).append(kwargs)


def _make_client(monkeypatch) -> tuple[SQSQueueClient, FakeSQSClient]:
    fake = FakeSQSClient()

    def fake_factory(_service, region_name):
        return fake

    monkeypatch.setattr("app.adapters.aws_queue_client.boto3.client", fake_factory)
    client = SQSQueueClient(region_name="us-east-1", queue_url="https://sqs.example.com/queue")
    return client, fake


def test_enqueue_sends_message(monkeypatch):
    client, fake = _make_client(monkeypatch)
    message = {"jobId": "job-1", "inputKey": "uploads/input.jpg"}

    client.enqueue(message)

    assert len(fake.calls["send_message"]) == 1
    call = fake.calls["send_message"][0]
    assert call["QueueUrl"] == "https://sqs.example.com/queue"
    assert json.loads(call["MessageBody"]) == message


def test_ping_success(monkeypatch):
    client, _ = _make_client(monkeypatch)

    assert client.ping() is True


def test_ping_failure(monkeypatch):
    client, fake = _make_client(monkeypatch)
    fake._fail_get_attrs = True

    assert client.ping() is False
