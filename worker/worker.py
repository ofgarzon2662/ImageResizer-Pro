import os
import time
from dataclasses import dataclass

from adapters.jobs_repo import SQLiteJobsRepository
from adapters.protocols import QueueConsumer, WorkerJobsRepository, WorkerStorageClient
from adapters.queue_client import RedisQueueConsumer
from adapters.storage_client import S3StorageClient
from image import ImageProcessor
from metrics import start_metrics_server
from processor import JobProcessor


@dataclass(frozen=True)
class Settings:
    minio_endpoint: str
    minio_access_key: str
    minio_secret_key: str
    minio_region: str
    minio_bucket: str
    redis_url: str
    redis_queue_name: str
    sqlite_path: str
    metrics_port: int


@dataclass(frozen=True)
class AWSSettings:
    aws_region: str
    input_bucket: str
    output_bucket: str
    queue_url: str
    table_name: str
    metrics_port: int


def load_settings() -> Settings:
    return Settings(
        minio_endpoint=os.getenv("MINIO_ENDPOINT", "http://minio:9000"),
        minio_access_key=os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
        minio_secret_key=os.getenv("MINIO_SECRET_KEY", "minioadmin"),
        minio_region=os.getenv("MINIO_REGION", "us-east-1"),
        minio_bucket=os.getenv("MINIO_BUCKET", "images"),
        redis_url=os.getenv("REDIS_URL", "redis://redis:6379/0"),
        redis_queue_name=os.getenv("REDIS_QUEUE_NAME", "image_jobs"),
        sqlite_path=os.getenv("SQLITE_PATH", "/tmp/imageresizer_jobs.db"),
        metrics_port=int(os.getenv("WORKER_METRICS_PORT", "9001")),
    )


def load_aws_settings() -> AWSSettings:
    return AWSSettings(
        aws_region=os.getenv("AWS_REGION", "us-east-1"),
        input_bucket=os.environ["JOBS_BUCKET_INPUT"],
        output_bucket=os.environ["JOBS_BUCKET_OUTPUT"],
        queue_url=os.environ["JOBS_QUEUE_URL"],
        table_name=os.environ["JOBS_TABLE_NAME"],
        metrics_port=int(os.getenv("WORKER_METRICS_PORT", "9001")),
    )


def _build_local_adapters(
    settings: Settings,
) -> tuple[QueueConsumer, WorkerStorageClient, WorkerJobsRepository]:
    queue_consumer = RedisQueueConsumer(settings.redis_url, settings.redis_queue_name)
    storage_client = S3StorageClient(
        endpoint_url=settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        region_name=settings.minio_region,
        bucket_name=settings.minio_bucket,
    )
    jobs_repo = SQLiteJobsRepository(settings.sqlite_path)
    return queue_consumer, storage_client, jobs_repo


def _build_aws_adapters(
    settings: AWSSettings,
) -> tuple[QueueConsumer, WorkerStorageClient, WorkerJobsRepository]:
    from adapters.aws_jobs_repo import DynamoDBJobsRepository
    from adapters.aws_queue_client import SQSQueueConsumer
    from adapters.aws_storage_client import AWSS3StorageClient

    queue_consumer = SQSQueueConsumer(
        region_name=settings.aws_region,
        queue_url=settings.queue_url,
    )
    storage_client = AWSS3StorageClient(
        region_name=settings.aws_region,
        input_bucket=settings.input_bucket,
        output_bucket=settings.output_bucket,
    )
    jobs_repo = DynamoDBJobsRepository(
        region_name=settings.aws_region,
        table_name=settings.table_name,
    )
    return queue_consumer, storage_client, jobs_repo


def main() -> None:
    environment = os.getenv("ENVIRONMENT", "local").lower()

    if environment == "aws":
        aws_settings = load_aws_settings()
        queue_consumer, storage_client, jobs_repo = _build_aws_adapters(aws_settings)
        start_metrics_server(aws_settings.metrics_port)
    else:
        local_settings = load_settings()
        queue_consumer, storage_client, jobs_repo = _build_local_adapters(local_settings)
        start_metrics_server(local_settings.metrics_port)

    image_processor = ImageProcessor()
    processor = JobProcessor(
        jobs_repo=jobs_repo,
        storage_client=storage_client,
        image_processor=image_processor,
    )

    while not queue_consumer.ping():
        time.sleep(1)

    queue_consumer.consume_forever(processor.process)


if __name__ == "__main__":
    main()
