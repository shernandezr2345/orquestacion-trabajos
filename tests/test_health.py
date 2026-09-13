from fastapi.testclient import TestClient

from orquestacion_trabajos.api.app import create_app


def test_health_live_returns_ok() -> None:
    app = create_app()
    with TestClient(app) as client:
        response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_ready_returns_ready_shape() -> None:
    app = create_app()
    with TestClient(app) as client:
        response = client.get("/health/ready")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ready"
    assert payload["database"] == "ready"
    assert payload["pulsar"] == "ready"
    assert isinstance(payload["consumers"], bool)
