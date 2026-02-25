from uuid import uuid4

from app.metrics import JOBS_CREATED_TOTAL, JOBS_ENQUEUED_TOTAL
from app.models import CreateJobRequest, CreateJobResponse, JobResponse, JobStatus


class JobNotFoundError(Exception):
    pass


class JobsService:
    def __init__(self, jobs_repo, queue_client, storage_client) -> None:
        self.jobs_repo = jobs_repo
        self.queue_client = queue_client
        self.storage_client = storage_client

    def create_job(self, request: CreateJobRequest) -> CreateJobResponse:
        if not request.input_key.startswith("uploads/"):
            raise ValueError("input_key must start with uploads/")
        if not self.storage_client.head(request.input_key):
            raise ValueError("input_key does not exist in object storage")

        job_id = str(uuid4())
        variants_payload = [
            {"name": variant.name, "width": variant.width, "format": variant.format.value}
            for variant in request.variants
        ]

        self.jobs_repo.create_job(
            job_id=job_id,
            input_key=request.input_key,
            variants=variants_payload,
        )
        JOBS_CREATED_TOTAL.inc()

        self.queue_client.enqueue(
            {
                "jobId": job_id,
                "inputKey": request.input_key,
                "variants": variants_payload,
            }
        )
        self.jobs_repo.update_status(job_id=job_id, status=JobStatus.QUEUED)
        JOBS_ENQUEUED_TOTAL.inc()

        return CreateJobResponse(job_id=job_id, status=JobStatus.QUEUED)

    def get_job(self, job_id: str) -> JobResponse:
        record = self.jobs_repo.get_job(job_id)
        if record is None:
            raise JobNotFoundError()
        return JobResponse.model_validate(record)
