import boto3
from botocore.client import Config


class S3StorageClient:
    def __init__(
        self,
        endpoint_url: str,
        access_key: str,
        secret_key: str,
        region_name: str,
        bucket_name: str,
    ) -> None:
        self.bucket_name = bucket_name
        self._client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region_name,
            config=Config(signature_version="s3v4"),
        )

    def download_bytes(self, key: str) -> bytes:
        response = self._client.get_object(Bucket=self.bucket_name, Key=key)
        return response["Body"].read()

    def upload_bytes(self, key: str, content_type: str, payload: bytes) -> None:
        self._client.put_object(
            Bucket=self.bucket_name,
            Key=key,
            Body=payload,
            ContentType=content_type,
        )
