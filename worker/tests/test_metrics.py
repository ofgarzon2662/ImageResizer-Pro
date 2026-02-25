from metrics import start_metrics_server


def test_start_metrics_server_delegates_to_prometheus(monkeypatch):
    calls = []

    def fake_start_http_server(port):
        calls.append(port)

    monkeypatch.setattr("metrics.start_http_server", fake_start_http_server)
    start_metrics_server(9200)
    assert calls == [9200]
