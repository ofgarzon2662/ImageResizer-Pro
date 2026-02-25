from fastapi import APIRouter, HTTPException, Request, status

from app.models import CreateJobRequest, CreateJobResponse, DownloadsResponse, JobResponse
from app.services.jobs_service import JobNotFoundError

router = APIRouter(prefix="/v1/jobs", tags=["jobs"])


@router.post("", response_model=CreateJobResponse, status_code=status.HTTP_201_CREATED)
def create_job(request_body: CreateJobRequest, request: Request) -> CreateJobResponse:
    try:
        return request.app.state.jobs_service.create_job(request_body)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


@router.get("/{job_id}", response_model=JobResponse)
def get_job(job_id: str, request: Request) -> JobResponse:
    try:
        return request.app.state.jobs_service.get_job(job_id)
    except JobNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="job not found") from error


@router.get("/{job_id}/downloads", response_model=DownloadsResponse)
def get_downloads(job_id: str, request: Request) -> DownloadsResponse:
    try:
        return request.app.state.downloads_service.get_downloads(job_id)
    except JobNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="job not found") from error
