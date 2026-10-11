from conftest import auth_headers, register_and_get_token

from app.models.ai_log import AILog


def test_ai_status_lists_all_providers_and_demo_always_ok(client):
    token = register_and_get_token(client)
    response = client.get("/api/ai/status", headers=auth_headers(token))
    assert response.status_code == 200
    body = response.json()

    names = {p["name"] for p in body["providers"]}
    assert names == {"demo", "local", "free_api", "openai", "gemini"}

    demo = next(p for p in body["providers"] if p["name"] == "demo")
    assert demo["connection_ok"] is True
    assert demo["label"] == "FREE"

    # zero-config: with nothing set, demo is both the active provider and fallback
    assert body["active_provider"] == "demo"
    assert body["active_fallback"] == "demo"


def test_ai_status_requires_auth(client):
    response = client.get("/api/ai/status")
    assert response.status_code == 401


def test_ai_test_pipeline_works_with_zero_config(client):
    token = register_and_get_token(client)
    response = client.post(
        "/api/ai/test",
        json={"text": "Hi, I need a quote for a new website, budget around $2000, fairly urgent"},
        headers=auth_headers(token),
    )
    assert response.status_code == 200
    body = response.json()

    assert body["provider_used"] == "demo"
    assert body["fallback_used"] is False
    assert 0 <= body["score"] <= 100
    assert isinstance(body["extracted"], dict)
    assert body["response_text"]  # never an empty response


def test_ai_test_pipeline_writes_audit_log(client):
    token = register_and_get_token(client)
    client.post("/api/ai/test", json={"text": "Need help urgently"}, headers=auth_headers(token))

    session = client.test_session_factory()
    try:
        logs = session.query(AILog).all()
    finally:
        session.close()

    operations = {log.operation for log in logs}
    assert {"classify", "extract", "score", "generate_response"}.issubset(operations)
    assert all(log.success for log in logs)
    assert all(log.actual_provider == "demo" for log in logs)


def test_switching_to_unreachable_provider_falls_back_to_demo_live(client):
    token = register_and_get_token(client)
    headers = auth_headers(token)

    # Point primary provider at "local" (no Ollama running in this environment)
    # with an explicit fallback to demo — mirrors "disable the provider, watch
    # it fall back live" from the demo script, without needing real internet.
    settings_response = client.patch(
        "/api/ai/settings", json={"ai_provider": "local", "ai_fallback_provider": "demo"}, headers=headers
    )
    assert settings_response.status_code == 200
    assert settings_response.json()["active_provider"] == "local"

    response = client.post("/api/ai/test", json={"text": "Need a quote"}, headers=headers)
    assert response.status_code == 200
    body = response.json()

    assert body["provider_used"] == "demo"
    assert body["fallback_used"] is True
    assert "local" in body["fallback_reason"]


def test_update_settings_rejects_unknown_provider(client):
    token = register_and_get_token(client)
    response = client.patch(
        "/api/ai/settings", json={"ai_provider": "some_made_up_provider"}, headers=auth_headers(token)
    )
    assert response.status_code == 400


def test_provider_settings_are_isolated_per_business(client):
    token_a = register_and_get_token(client, email="ownera@techfixsolutions.io", business_name="Biz A")
    token_b = register_and_get_token(client, email="ownerb@techfixsolutions.io", business_name="Biz B")

    client.patch("/api/ai/settings", json={"ai_provider": "local"}, headers=auth_headers(token_a))

    status_a = client.get("/api/ai/status", headers=auth_headers(token_a)).json()
    status_b = client.get("/api/ai/status", headers=auth_headers(token_b)).json()

    assert status_a["active_provider"] == "local"
    assert status_b["active_provider"] == "demo"
