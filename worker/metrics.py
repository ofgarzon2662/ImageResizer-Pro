from prometheus_client import Counter, Histogram, start_http_server

JOBS_COMPLETED_TOTAL = Counter(
    "jobs_completed_total",
    "Total number of successfully completed jobs.",
)
JOBS_FAILED_TOTAL = Counter(
    "jobs_failed_total",
    "Total number of failed jobs.",
)
JOB_PROCESSING_DURATION_SECONDS = Histogram(
    "job_processing_duration_seconds",
    "Duration spent processing a single job.",
)


def start_metrics_server(port: int) -> None:
    start_http_server(port)
