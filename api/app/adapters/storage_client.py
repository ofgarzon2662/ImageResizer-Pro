import boto3
from botocore.client import Config
from botocore.exceptions import ClientError


class S3StorageClient:
    def __init__(
        self,
        endpoint_url: str,
        access_key: str,
        secret_key: str,
        region_name: str,
        bucket_name: str,
        public_endpoint_url: str | None = None,
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
        if public_endpoint_url:
            self._presign_client = boto3.client(
                "s3",
                endpoint_url=public_endpoint_url,
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                region_name=region_name,
                config=Config(signature_version="s3v4"),
            )
        else:
            self._presign_client = self._client

    def presign_put(self, key: str, content_type: str, ttl_seconds: int) -> str:
        return self._presign_client.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": self.bucket_name,
                "Key": key,
                "ContentType": content_type,
            },
            ExpiresIn=ttl_seconds,
        )

    def presign_get(self, key: str, ttl_seconds: int) -> str:
        return self._presign_client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": self.bucket_name,
                "Key": key,
            },
            ExpiresIn=ttl_seconds,
        )

    def head(self, key: str) -> bool:
        try:
            self._client.head_object(Bucket=self.bucket_name, Key=key)
            return True
        except ClientError:
            return False

    def ping(self) -> bool:
        try:
            self._client.head_bucket(Bucket=self.bucket_name)
            return True
        except Exception:
            return False
