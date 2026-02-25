def test_healthz_ok(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readyz_ok_when_dependencies_ready(client):
    client.app.state.health_service.ready = True
    response = client.get("/readyz")
    assert response.status_code == 200


def test_readyz_unavailable_when_dependencies_not_ready(client):
    client.app.state.health_service.ready = False
    response = client.get("/readyz")
    assert response.status_code == 503


def test_metrics_exposes_prometheus_payload(client):
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "jobs_created_total" in response.text
    assert "jobs_enqueued_total" in response.text
