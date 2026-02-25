from adapters.storage_client import S3StorageClient


class FakeBody:
    def __init__(self, payload: bytes):
        self._payload = payload

    def read(self):
        return self._payload


class FakeS3:
    def __init__(self):
        self.put_calls = []

    def get_object(self, Bucket, Key):
        return {"Body": FakeBody(f"{Bucket}:{Key}".encode())}

    def put_object(self, Bucket, Key, Body, ContentType):
        self.put_calls.append((Bucket, Key, Body, ContentType))


def test_storage_client_download_and_upload(monkeypatch):
    fake_s3 = FakeS3()

    def fake_boto_client(_service, **_kwargs):
        return fake_s3

    monkeypatch.setattr("adapters.storage_client.boto3.client", fake_boto_client)
    client = S3StorageClient(
        endpoint_url="http://minio:9000",
        access_key="k",
        secret_key="s",
        region_name="us-east-1",
        bucket_name="images",
    )

    data = client.download_bytes("uploads/input.jpg")
    client.upload_bytes("outputs/job/thumb.webp", "image/webp", b"binary")

    assert data == b"images:uploads/input.jpg"
    assert len(fake_s3.put_calls) == 1
    assert fake_s3.put_calls[0][1] == "outputs/job/thumb.webp"
