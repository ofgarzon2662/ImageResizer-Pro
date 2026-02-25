from prometheus_client import CONTENT_TYPE_LATEST, Counter, generate_latest

JOBS_CREATED_TOTAL = Counter(
    "jobs_created_total",
    "Total number of created jobs.",
)
JOBS_ENQUEUED_TOTAL = Counter(
    "jobs_enqueued_total",
    "Total number of enqueued jobs.",
)


def render_metrics() -> tuple[bytes, str]:
    return generate_latest(), CONTENT_TYPE_LATEST
