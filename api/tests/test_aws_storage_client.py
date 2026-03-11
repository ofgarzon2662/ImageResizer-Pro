from botocore.exceptions import ClientError

from app.adapters.aws_storage_client import AWSS3StorageClient


class FakeS3Client:
    def __init__(self):
        self.calls = {}
        self._fail_head_object = False
        self._fail_head_bucket = False

    def generate_presigned_url(self, operation_name, Params, ExpiresIn):
        self.calls.setdefault("presign", []).append(
            (operation_name, Params, ExpiresIn)
        )
        return f"https://s3.example.com/{operation_name}/{Params['Bucket']}/{Params['Key']}"

    def head_object(self, Bucket, Key):
        if self._fail_head_object:
            raise ClientError(
                {"Error": {"Code": "404", "Message": "Not Found"}}, "HeadObject"
            )
        self.calls.setdefault("head_object", []).append((Bucket, Key))

    def head_bucket(self, Bucket):
        if self._fail_head_bucket:
            raise RuntimeError("bucket not found")
        self.calls.setdefault("head_bucket", []).append(Bucket)


def _make_client(monkeypatch) -> tuple[AWSS3StorageClient, FakeS3Client]:
    fake = FakeS3Client()

    def fake_factory(_service, region_name):
        return fake

    monkeypatch.setattr("app.adapters.aws_storage_client.boto3.client", fake_factory)
    client = AWSS3StorageClient(
        region_name="us-east-1",
        input_bucket="my-input",
        output_bucket="my-output",
    )
    return client, fake


def test_bucket_for_key_routes_correctly(monkeypatch):
    client, _ = _make_client(monkeypatch)

    assert client._bucket_for_key("uploads/input.jpg") == "my-input"
    assert client._bucket_for_key("outputs/job-1/thumb.webp") == "my-output"
    assert client._bucket_for_key("other/key") == "my-input"


def test_presign_put(monkeypatch):
    client, fake = _make_client(monkeypatch)

    url = client.presign_put("uploads/input.jpg", "image/jpeg", 300)

    assert "put_object" in url
    assert "my-input" in url
    call = fake.calls["presign"][0]
    assert call[0] == "put_object"
    assert call[1]["ContentType"] == "image/jpeg"
    assert call[2] == 300


def test_presign_put_output_bucket(monkeypatch):
    client, fake = _make_client(monkeypatch)

    url = client.presign_put("outputs/job-1/thumb.webp", "image/webp", 600)

    assert "my-output" in url


def test_presign_get(monkeypatch):
    client, fake = _make_client(monkeypatch)

    url = client.presign_get("uploads/input.jpg", 500)

    assert "get_object" in url
    call = fake.calls["presign"][0]
    assert call[0] == "get_object"
    assert call[1]["Key"] == "uploads/input.jpg"
    assert call[2] == 500


def test_head_exists(monkeypatch):
    client, _ = _make_client(monkeypatch)

    assert client.head("uploads/input.jpg") is True


def test_head_not_found(monkeypatch):
    client, fake = _make_client(monkeypatch)
    fake._fail_head_object = True

    assert client.head("uploads/missing.jpg") is False


def test_ping_success(monkeypatch):
    client, _ = _make_client(monkeypatch)

    assert client.ping() is True


def test_ping_failure(monkeypatch):
    client, fake = _make_client(monkeypatch)
    fake._fail_head_bucket = True

    assert client.ping() is False
