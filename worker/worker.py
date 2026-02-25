import os
import time
from dataclasses import dataclass

from adapters.jobs_repo import SQLiteJobsRepository
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


def main() -> None:
    settings = load_settings()
    start_metrics_server(settings.metrics_port)

    queue_consumer = RedisQueueConsumer(settings.redis_url, settings.redis_queue_name)
    storage_client = S3StorageClient(
        endpoint_url=settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        region_name=settings.minio_region,
        bucket_name=settings.minio_bucket,
    )
    jobs_repo = SQLiteJobsRepository(settings.sqlite_path)
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
