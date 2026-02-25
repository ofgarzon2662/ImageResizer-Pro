from fastapi import APIRouter, Request, Response, status

from app.metrics import render_metrics

router = APIRouter()


@router.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/readyz")
def readyz(request: Request) -> Response:
    if request.app.state.health_service.is_ready():
        return Response(status_code=status.HTTP_200_OK)
    return Response(status_code=status.HTTP_503_SERVICE_UNAVAILABLE)


@router.get("/metrics")
def metrics() -> Response:
    payload, content_type = render_metrics()
    return Response(content=payload, media_type=content_type)
