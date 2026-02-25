from app.models import DownloadItem, DownloadsResponse, JobStatus, VariantStatus
from app.services.jobs_service import JobNotFoundError


class DownloadsService:
    def __init__(self, jobs_repo, storage_client, presign_ttl_seconds: int) -> None:
        self.jobs_repo = jobs_repo
        self.storage_client = storage_client
        self.presign_ttl_seconds = presign_ttl_seconds

    def get_downloads(self, job_id: str) -> DownloadsResponse:
        record = self.jobs_repo.get_job(job_id)
        if record is None:
            raise JobNotFoundError()

        if record["status"] not in {JobStatus.DONE.value, JobStatus.FAILED.value}:
            return DownloadsResponse(job_id=job_id, downloads=[])

        downloads: list[DownloadItem] = []
        for variant in record["variants"]:
            if variant["status"] == VariantStatus.DONE.value and variant["output_key"]:
                downloads.append(
                    DownloadItem(
                        name=variant["name"],
                        output_key=variant["output_key"],
                        download_url=self.storage_client.presign_get(
                            key=variant["output_key"],
                            ttl_seconds=self.presign_ttl_seconds,
                        ),
                        expires_in_seconds=self.presign_ttl_seconds,
                    )
                )

        return DownloadsResponse(job_id=job_id, downloads=downloads)
