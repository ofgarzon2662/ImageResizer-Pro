class HealthService:
    def __init__(self, storage_client, queue_client, jobs_repo) -> None:
        self.storage_client = storage_client
        self.queue_client = queue_client
        self.jobs_repo = jobs_repo

    def is_ready(self) -> bool:
        return (
            self.storage_client.ping()
            and self.queue_client.ping()
            and self.jobs_repo.ping()
        )
