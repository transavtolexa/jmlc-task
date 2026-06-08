from fastapi.testclient import TestClient

from app.main import app


def test_health() -> None:
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_restore_endpoint() -> None:
    client = TestClient(app)

    response = client.post("/restore", json={"text": "куплюайфон14про"})

    assert response.status_code == 200
    assert response.json()["text"] == "куплюайфон14про"
    assert "айфон" in response.json()["restored"]

