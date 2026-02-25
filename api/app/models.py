from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class JobStatus(str, Enum):
    CREATED = "CREATED"
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    DONE = "DONE"
    FAILED = "FAILED"


class VariantFormat(str, Enum):
    JPEG = "jpeg"
    PNG = "png"
    WEBP = "webp"


class VariantStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    DONE = "DONE"
    FAILED = "FAILED"


class CreateUploadRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    filename: str = Field(min_length=1, max_length=255)
    content_type: str = Field(
        default="application/octet-stream",
        alias="contentType",
        min_length=1,
        max_length=255,
    )


class CreateUploadResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    upload_url: str = Field(alias="uploadUrl")
    input_key: str = Field(alias="inputKey")
    expires_in_seconds: int = Field(alias="expiresInSeconds")


class JobVariantRequest(BaseModel):
    name: str = Field(min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$")
    width: int = Field(ge=64, le=2048)
    format: VariantFormat


class CreateJobRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    input_key: str = Field(alias="inputKey", min_length=1, max_length=1024)
    variants: list[JobVariantRequest] = Field(min_length=1, max_length=5)

    @model_validator(mode="after")
    def validate_unique_variant_names(self) -> "CreateJobRequest":
        names = [variant.name for variant in self.variants]
        unique_names = set(names)
        if len(unique_names) != len(names):
            raise ValueError("variant names must be unique within a job")
        return self


class CreateJobResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    job_id: str = Field(alias="jobId")
    status: JobStatus


class JobVariantResponse(BaseModel):
    name: str
    width: int
    format: VariantFormat
    status: VariantStatus
    output_key: Optional[str] = Field(default=None, alias="outputKey")
    error: Optional[str] = None


class JobResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    job_id: str = Field(alias="jobId")
    input_key: str = Field(alias="inputKey")
    status: JobStatus
    variants: list[JobVariantResponse]
    error: Optional[str] = None
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")


class DownloadItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str
    output_key: str = Field(alias="outputKey")
    download_url: str = Field(alias="downloadUrl")
    expires_in_seconds: int = Field(alias="expiresInSeconds")


class DownloadsResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    job_id: str = Field(alias="jobId")
    downloads: list[DownloadItem]
