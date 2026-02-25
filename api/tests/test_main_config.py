from app.main import load_settings


def test_load_settings_reads_env(monkeypatch):
    monkeypatch.setenv("MINIO_ENDPOINT", "http://storage:9000")
    monkeypatch.setenv("MINIO_PUBLIC_ENDPOINT", "http://localhost:9000")
    monkeypatch.setenv("PRESIGN_TTL_SECONDS", "1200")

    settings = load_settings()

    assert settings.minio_endpoint == "http://storage:9000"
    assert settings.minio_public_endpoint == "http://localhost:9000"
    assert settings.presign_ttl_seconds == 1200
