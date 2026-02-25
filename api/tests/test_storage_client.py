from app.adapters.storage_client import S3StorageClient
from botocore.exceptions import ClientError


class FakeS3Client:
    def __init__(self, endpoint_url):
        self.endpoint_url = endpoint_url
        self.calls = []

    def generate_presigned_url(self, operation_name, Params, ExpiresIn):
        self.calls.append((operation_name, Params, ExpiresIn))
        return f"{self.endpoint_url}/signed/{operation_name}/{Params['Key']}"

    def head_object(self, Bucket, Key):
        if Key == "missing":
            raise ClientError({"Error": {"Code": "404", "Message": "Not Found"}}, "HeadObject")
        return {"Bucket": Bucket, "Key": Key}

    def head_bucket(self, Bucket):
        if Bucket == "bad":
            raise RuntimeError("bad")
        return {"Bucket": Bucket}


def test_storage_client_presign_uses_public_endpoint(monkeypatch):
    created_clients = []

    def fake_boto_client(_service, endpoint_url, **_kwargs):
        client = FakeS3Client(endpoint_url)
        created_clients.append(client)
        return client

    monkeypatch.setattr("app.adapters.storage_client.boto3.client", fake_boto_client)
    client = S3StorageClient(
        endpoint_url="http://minio:9000",
        public_endpoint_url="http://localhost:9000",
        access_key="k",
        secret_key="s",
        region_name="us-east-1",
        bucket_name="images",
    )

    put_url = client.presign_put("uploads/key.jpg", "image/jpeg", 300)
    get_url = client.presign_get("uploads/key.jpg", 300)

    assert put_url.startswith("http://localhost:9000/")
    assert get_url.startswith("http://localhost:9000/")
    assert len(created_clients) == 2


def test_storage_client_head_and_ping(monkeypatch):
    fake_client = FakeS3Client("http://minio:9000")

    def fake_boto_client(_service, endpoint_url, **_kwargs):
        return fake_client

    monkeypatch.setattr("app.adapters.storage_client.boto3.client", fake_boto_client)
    client = S3StorageClient(
        endpoint_url="http://minio:9000",
        access_key="k",
        secret_key="s",
        region_name="us-east-1",
        bucket_name="images",
    )

    assert client.head("exists")
    assert not client.head("missing")
    assert client.ping()

    client.bucket_name = "bad"
    assert not client.ping()
