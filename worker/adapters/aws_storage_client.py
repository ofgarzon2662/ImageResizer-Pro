import boto3


class AWSS3StorageClient:
    """Dual-bucket S3 client using IAM task role credentials (no explicit keys)."""

    def __init__(
        self, region_name: str, input_bucket: str, output_bucket: str
    ) -> None:
        self.input_bucket = input_bucket
        self.output_bucket = output_bucket
        self._client = boto3.client("s3", region_name=region_name)

    def _bucket_for_key(self, key: str) -> str:
        if key.startswith("outputs/"):
            return self.output_bucket
        return self.input_bucket

    def download_bytes(self, key: str) -> bytes:
        response = self._client.get_object(
            Bucket=self._bucket_for_key(key), Key=key
        )
        return response["Body"].read()

    def upload_bytes(self, key: str, content_type: str, payload: bytes) -> None:
        self._client.put_object(
            Bucket=self._bucket_for_key(key),
            Key=key,
            Body=payload,
            ContentType=content_type,
        )
