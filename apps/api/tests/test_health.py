from fastapi.testclient import TestClient

from app.main import app


def test_health_endpoint_reports_service_status() -> None:
    client = TestClient(app)

    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "vocabulary-story-learning-api",
    }
