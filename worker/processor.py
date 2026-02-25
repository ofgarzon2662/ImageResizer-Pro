from metrics import (
    JOB_PROCESSING_DURATION_SECONDS,
    JOBS_COMPLETED_TOTAL,
    JOBS_FAILED_TOTAL,
)


class JobProcessor:
    def __init__(self, jobs_repo, storage_client, image_processor) -> None:
        self.jobs_repo = jobs_repo
        self.storage_client = storage_client
        self.image_processor = image_processor

    def process(self, message: dict) -> None:
        with JOB_PROCESSING_DURATION_SECONDS.time():
            job_id = message["jobId"]
            input_key = message["inputKey"]
            variants = message["variants"]
            active_variant_name = None
            try:
                self.jobs_repo.update_job_status(job_id, "RUNNING")
                source_bytes = self.storage_client.download_bytes(input_key)

                for variant in variants:
                    variant_name = variant["name"]
                    active_variant_name = variant_name
                    width = int(variant["width"])
                    variant_format = variant["format"]
                    output_key = f"outputs/{job_id}/{variant_name}.{variant_format}"
                    self.jobs_repo.update_variant_status(job_id, variant_name, "RUNNING")
                    output_bytes = self.image_processor.create_variant(
                        image_bytes=source_bytes,
                        width=width,
                        output_format=variant_format,
                    )
                    content_type = _content_type_for_format(variant_format)
                    self.storage_client.upload_bytes(output_key, content_type, output_bytes)
                    self.jobs_repo.update_variant_status(
                        job_id,
                        variant_name,
                        "DONE",
                        output_key=output_key,
                    )
                    active_variant_name = None

                self.jobs_repo.update_job_status(job_id, "DONE")
                JOBS_COMPLETED_TOTAL.inc()
            except Exception as error:
                if active_variant_name is not None:
                    self.jobs_repo.update_variant_status(
                        job_id,
                        active_variant_name,
                        "FAILED",
                        error=str(error),
                    )
                self.jobs_repo.update_job_status(job_id, "FAILED", error=str(error))
                JOBS_FAILED_TOTAL.inc()
                raise


def _content_type_for_format(image_format: str) -> str:
    if image_format == "jpeg":
        return "image/jpeg"
    if image_format == "png":
        return "image/png"
    if image_format == "webp":
        return "image/webp"
    return "application/octet-stream"
