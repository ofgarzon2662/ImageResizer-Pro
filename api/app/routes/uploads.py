from fastapi import APIRouter, Request

from app.models import CreateUploadRequest, CreateUploadResponse

router = APIRouter(prefix="/v1/uploads", tags=["uploads"])


@router.post("", response_model=CreateUploadResponse)
def create_upload(request_body: CreateUploadRequest, request: Request) -> CreateUploadResponse:
    return request.app.state.uploads_service.create_upload(request_body)
