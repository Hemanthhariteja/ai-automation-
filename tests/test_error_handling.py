from conftest import auth_headers, register_and_get_token
from fastapi.testclient import TestClient

from app.database.session import get_db
from app.main import app


def _broken_get_db():
    raise RuntimeError("simulated unexpected bug")
    yield  # pragma: no cover — required to keep this a generator like the real dependency


def test_unhandled_exception_returns_clean_json_not_a_stack_trace(client):
    """Forces a genuinely unexpected exception (not an HTTPException) via a
    broken dependency and confirms the client sees a generic message + a
    request id — never a traceback — while the real detail is still logged
    server-side (see the request-logging middleware).

    Uses a fresh TestClient with raise_server_exceptions=False: the default
    `client` fixture re-raises server exceptions (useful for catching real
    bugs in other tests), which would bypass the very handler this test
    exists to verify — a real HTTP client would see the JSON response, not
    a re-raised exception, so that's what this test needs too."""
    token = register_and_get_token(client)

    app.dependency_overrides[get_db] = _broken_get_db
    lenient_client = TestClient(app, raise_server_exceptions=False)
    response = lenient_client.get("/api/leads", headers=auth_headers(token))

    assert response.status_code == 500
    body = response.json()
    assert body["detail"] == "An unexpected error occurred. Please try again."
    assert "request_id" in body
    assert "RuntimeError" not in response.text
    assert "Traceback" not in response.text


def test_response_includes_request_id_header(client):
    response = client.get("/api/health")
    assert "X-Request-ID" in response.headers
    assert len(response.headers["X-Request-ID"]) == 12


def test_health_check_reports_db_connectivity(client):
    response = client.get("/api/health")
    body = response.json()
    assert body["status"] == "ok"
    assert body["db_connected"] is True
    assert "uptime_seconds" in body
