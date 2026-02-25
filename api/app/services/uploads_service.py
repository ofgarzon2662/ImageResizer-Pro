from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from app.models import CreateUploadRequest, CreateUploadResponse


class UploadsService:
    def __init__(self, storage_client, presign_ttl_seconds: int) -> None:
        self.storage_client = storage_client
        self.presign_ttl_seconds = presign_ttl_seconds

    def create_upload(self, request: CreateUploadRequest) -> CreateUploadResponse:
        now = datetime.now(timezone.utc)
        safe_filename = Path(request.filename).name.replace(" ", "_")
        key = f"uploads/{now:%Y/%m/%d}/{uuid4()}-{safe_filename}"
        upload_url = self.storage_client.presign_put(
            key=key,
            content_type=request.content_type,
            ttl_seconds=self.presign_ttl_seconds,
        )
        return CreateUploadResponse(
            upload_url=upload_url,
            input_key=key,
            expires_in_seconds=self.presign_ttl_seconds,
        )
