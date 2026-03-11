import os
from dataclasses import dataclass

from fastapi import FastAPI

from app.adapters.jobs_repo import SQLiteJobsRepository
from app.adapters.protocols import JobsRepository, QueueClient, StorageClient
from app.adapters.queue_client import RedisQueueClient
from app.adapters.storage_client import S3StorageClient
from app.routes.health import router as health_router
from app.routes.jobs import router as jobs_router
from app.routes.uploads import router as uploads_router
from app.services.downloads_service import DownloadsService
from app.services.health_service import HealthService
from app.services.jobs_service import JobsService
from app.services.uploads_service import UploadsService


@dataclass(frozen=True)
class Settings:
    minio_endpoint: str
    minio_public_endpoint: str | None
    minio_access_key: str
    minio_secret_key: str
    minio_region: str
    minio_bucket: str
    redis_url: str
    redis_queue_name: str
    sqlite_path: str
    presign_ttl_seconds: int


@dataclass(frozen=True)
class AWSSettings:
    aws_region: str
    input_bucket: str
    output_bucket: str
    queue_url: str
    table_name: str
    presign_ttl_seconds: int


def load_settings() -> Settings:
    minio_public_endpoint = os.getenv("MINIO_PUBLIC_ENDPOINT")
    if minio_public_endpoint == "":
        minio_public_endpoint = None
    return Settings(
        minio_endpoint=os.getenv("MINIO_ENDPOINT", "http://minio:9000"),
        minio_public_endpoint=minio_public_endpoint,
        minio_access_key=os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
        minio_secret_key=os.getenv("MINIO_SECRET_KEY", "minioadmin"),
        minio_region=os.getenv("MINIO_REGION", "us-east-1"),
        minio_bucket=os.getenv("MINIO_BUCKET", "images"),
        redis_url=os.getenv("REDIS_URL", "redis://redis:6379/0"),
        redis_queue_name=os.getenv("REDIS_QUEUE_NAME", "image_jobs"),
        sqlite_path=os.getenv("SQLITE_PATH", "/tmp/imageresizer_jobs.db"),
        presign_ttl_seconds=int(os.getenv("PRESIGN_TTL_SECONDS", "900")),
    )


def load_aws_settings() -> AWSSettings:
    return AWSSettings(
        aws_region=os.getenv("AWS_REGION", "us-east-1"),
        input_bucket=os.environ["JOBS_BUCKET_INPUT"],
        output_bucket=os.environ["JOBS_BUCKET_OUTPUT"],
        queue_url=os.environ["JOBS_QUEUE_URL"],
        table_name=os.environ["JOBS_TABLE_NAME"],
        presign_ttl_seconds=int(os.getenv("PRESIGN_TTL_SECONDS", "900")),
    )


def _build_local_adapters(
    settings: Settings,
) -> tuple[StorageClient, QueueClient, JobsRepository, int]:
    storage_client = S3StorageClient(
        endpoint_url=settings.minio_endpoint,
        public_endpoint_url=settings.minio_public_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        region_name=settings.minio_region,
        bucket_name=settings.minio_bucket,
    )
    queue_client = RedisQueueClient(
        redis_url=settings.redis_url,
        queue_name=settings.redis_queue_name,
    )
    jobs_repo = SQLiteJobsRepository(db_path=settings.sqlite_path)
    return storage_client, queue_client, jobs_repo, settings.presign_ttl_seconds


def _build_aws_adapters(
    settings: AWSSettings,
) -> tuple[StorageClient, QueueClient, JobsRepository, int]:
    from app.adapters.aws_jobs_repo import DynamoDBJobsRepository
    from app.adapters.aws_queue_client import SQSQueueClient
    from app.adapters.aws_storage_client import AWSS3StorageClient

    storage_client = AWSS3StorageClient(
        region_name=settings.aws_region,
        input_bucket=settings.input_bucket,
        output_bucket=settings.output_bucket,
    )
    queue_client = SQSQueueClient(
        region_name=settings.aws_region,
        queue_url=settings.queue_url,
    )
    jobs_repo = DynamoDBJobsRepository(
        region_name=settings.aws_region,
        table_name=settings.table_name,
    )
    return storage_client, queue_client, jobs_repo, settings.presign_ttl_seconds


def create_app() -> FastAPI:
    environment = os.getenv("ENVIRONMENT", "local").lower()

    if environment == "aws":
        aws_settings = load_aws_settings()
        storage_client, queue_client, jobs_repo, presign_ttl = _build_aws_adapters(
            aws_settings
        )
        settings: Settings | AWSSettings = aws_settings
    else:
        local_settings = load_settings()
        storage_client, queue_client, jobs_repo, presign_ttl = _build_local_adapters(
            local_settings
        )
        settings = local_settings

    uploads_service = UploadsService(
        storage_client=storage_client,
        presign_ttl_seconds=presign_ttl,
    )
    jobs_service = JobsService(
        jobs_repo=jobs_repo,
        queue_client=queue_client,
        storage_client=storage_client,
    )
    downloads_service = DownloadsService(
        jobs_repo=jobs_repo,
        storage_client=storage_client,
        presign_ttl_seconds=presign_ttl,
    )
    health_service = HealthService(
        storage_client=storage_client,
        queue_client=queue_client,
        jobs_repo=jobs_repo,
    )

    app = FastAPI(title="ImageResizer-Pro API", version="0.1.0")
    app.state.settings = settings
    app.state.storage_client = storage_client
    app.state.queue_client = queue_client
    app.state.jobs_repo = jobs_repo
    app.state.uploads_service = uploads_service
    app.state.jobs_service = jobs_service
    app.state.downloads_service = downloads_service
    app.state.health_service = health_service

    app.include_router(health_router)
    app.include_router(uploads_router)
    app.include_router(jobs_router)
    return app


app = create_app()
