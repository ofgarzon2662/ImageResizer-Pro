from adapters.aws_storage_client import AWSS3StorageClient


class FakeBody:
    def __init__(self, payload: bytes):
        self._payload = payload

    def read(self):
        return self._payload


class FakeS3Client:
    def __init__(self):
        self.calls = {}

    def get_object(self, Bucket, Key):
        self.calls.setdefault("get_object", []).append((Bucket, Key))
        return {"Body": FakeBody(f"{Bucket}:{Key}".encode())}

    def put_object(self, Bucket, Key, Body, ContentType):
        self.calls.setdefault("put_object", []).append(
            (Bucket, Key, Body, ContentType)
        )


def _make_client(monkeypatch) -> tuple[AWSS3StorageClient, FakeS3Client]:
    fake = FakeS3Client()

    def fake_factory(_service, region_name):
        return fake

    monkeypatch.setattr("adapters.aws_storage_client.boto3.client", fake_factory)
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
    assert client._bucket_for_key("other/path") == "my-input"


def test_download_bytes(monkeypatch):
    client, fake = _make_client(monkeypatch)

    data = client.download_bytes("uploads/input.jpg")

    assert data == b"my-input:uploads/input.jpg"
    assert len(fake.calls["get_object"]) == 1
    assert fake.calls["get_object"][0] == ("my-input", "uploads/input.jpg")


def test_download_bytes_output_bucket(monkeypatch):
    client, fake = _make_client(monkeypatch)

    data = client.download_bytes("outputs/job-1/thumb.webp")

    assert data == b"my-output:outputs/job-1/thumb.webp"
    assert fake.calls["get_object"][0][0] == "my-output"


def test_upload_bytes(monkeypatch):
    client, fake = _make_client(monkeypatch)

    client.upload_bytes("outputs/job-1/thumb.webp", "image/webp", b"binary-data")

    assert len(fake.calls["put_object"]) == 1
    call = fake.calls["put_object"][0]
    assert call[0] == "my-output"
    assert call[1] == "outputs/job-1/thumb.webp"
    assert call[2] == b"binary-data"
    assert call[3] == "image/webp"


def test_upload_bytes_input_bucket(monkeypatch):
    client, fake = _make_client(monkeypatch)

    client.upload_bytes("uploads/file.jpg", "image/jpeg", b"data")

    assert fake.calls["put_object"][0][0] == "my-input"
