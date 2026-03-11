from collections.abc import Callable
from typing import Protocol


class QueueConsumer(Protocol):
    def consume_forever(self, handler: Callable[[dict], None]) -> None: ...
    def ping(self) -> bool: ...


class WorkerJobsRepository(Protocol):
    def update_job_status(
        self, job_id: str, status: str, error: str | None = None
    ) -> None: ...
    def update_variant_status(
        self,
        job_id: str,
        variant_name: str,
        status: str,
        output_key: str | None = None,
        error: str | None = None,
    ) -> None: ...


class WorkerStorageClient(Protocol):
    def download_bytes(self, key: str) -> bytes: ...
    def upload_bytes(self, key: str, content_type: str, payload: bytes) -> None: ...
