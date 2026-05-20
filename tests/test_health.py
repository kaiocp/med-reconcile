"""Smoke tests for the /health endpoint — verifies the service boots and responds."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_endpoint_returns_status_ok() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_endpoint_returns_json_content_type() -> None:
    response = client.get("/health")

    assert response.headers["content-type"] == "application/json"
