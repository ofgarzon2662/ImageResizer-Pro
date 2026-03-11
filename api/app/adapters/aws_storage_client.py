import boto3
from botocore.exceptions import ClientError


class AWSS3StorageClient:
    """Dual-bucket S3 client that relies on IAM task role credentials (no explicit keys)."""

    def __init__(self, region_name: str, input_bucket: str, output_bucket: str) -> None:
        self.input_bucket = input_bucket
        self.output_bucket = output_bucket
        self._client = boto3.client("s3", region_name=region_name)

    def _bucket_for_key(self, key: str) -> str:
        if key.startswith("outputs/"):
            return self.output_bucket
        return self.input_bucket

    def presign_put(self, key: str, content_type: str, ttl_seconds: int) -> str:
        return self._client.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": self._bucket_for_key(key),
                "Key": key,
                "ContentType": content_type,
            },
            ExpiresIn=ttl_seconds,
        )

    def presign_get(self, key: str, ttl_seconds: int) -> str:
        return self._client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": self._bucket_for_key(key),
                "Key": key,
            },
            ExpiresIn=ttl_seconds,
        )

    def head(self, key: str) -> bool:
        try:
            self._client.head_object(Bucket=self._bucket_for_key(key), Key=key)
            return True
        except ClientError:
            return False

    def ping(self) -> bool:
        try:
            self._client.head_bucket(Bucket=self.input_bucket)
            return True
        except Exception:
            return False
