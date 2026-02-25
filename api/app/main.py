import os
from dataclasses import dataclass

from fastapi import FastAPI

from app.adapters.jobs_repo import SQLiteJobsRepository
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


def create_app() -> FastAPI:
    settings = load_settings()

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

    uploads_service = UploadsService(
        storage_client=storage_client,
        presign_ttl_seconds=settings.presign_ttl_seconds,
    )
    jobs_service = JobsService(
        jobs_repo=jobs_repo,
        queue_client=queue_client,
        storage_client=storage_client,
    )
    downloads_service = DownloadsService(
        jobs_repo=jobs_repo,
        storage_client=storage_client,
        presign_ttl_seconds=settings.presign_ttl_seconds,
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
