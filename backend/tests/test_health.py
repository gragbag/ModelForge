"""
A first test for the /health endpoint.

Why this matters now: the moment this test exists, the guarded `backend` job in
your .github/workflows/ci.yml turns ON — every push will run ruff + mypy +
pytest against your backend automatically. This is your first real taste of CI.

FastAPI gives us a TestClient that calls the app in-process (no running server
needed), so tests are fast and isolated — exactly what CI wants.
"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_ok():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
