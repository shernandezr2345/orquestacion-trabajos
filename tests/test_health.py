from fastapi.testclient import TestClient

from orquestacion_trabajos.api.app import create_app
from orquestacion_trabajos.config.settings import Settings


def test_liveness_and_disabled_readiness():
    with TestClient(create_app(Settings(database_url=None))) as client:
        assert client.get("/health/live").json()["status"] == "ok"
        assert client.get("/health/ready").status_code == 503
