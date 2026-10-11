from conftest import auth_headers, register_and_get_token


def _create_workflow(client, headers):
    return client.post("/api/workflows", json={"name": "wf", "trigger_type": "manual"}, headers=headers).json()


def _add_node(client, headers, workflow_id, node_type, order_index, config=None):
    return client.post(
        f"/api/workflows/{workflow_id}/nodes",
        json={"node_type": node_type, "order_index": order_index, "config": config},
        headers=headers,
    ).json()


def test_ai_processor_skips_already_classified_lead(client):
    token = register_and_get_token(client)
    headers = auth_headers(token)
    lead = client.post("/api/leads", json={"raw_message": "I need a quote"}, headers=headers).json()
    assert lead["intent"] is not None  # classified on creation

    workflow = _create_workflow(client, headers)
    _add_node(client, headers, workflow["id"], "ai_processor", 0, {"force": False})

    response = client.post(f"/api/workflows/{workflow['id']}/run", json={"lead_id": lead["id"]}, headers=headers)
    assert response.json()["log"]["steps"][0]["detail"] == "Lead already classified — skipped re-run"


def test_ai_processor_skips_lead_with_no_message(client):
    token = register_and_get_token(client)
    headers = auth_headers(token)
    lead = client.post("/api/leads", json={}, headers=headers).json()
    assert lead["raw_message"] is None

    workflow = _create_workflow(client, headers)
    _add_node(client, headers, workflow["id"], "ai_processor", 0)

    response = client.post(f"/api/workflows/{workflow['id']}/run", json={"lead_id": lead["id"]}, headers=headers)
    assert response.json()["log"]["steps"][0]["detail"] == "Lead has no message to classify — skipped"


def test_generate_ai_response_action_skips_lead_with_no_message(client):
    token = register_and_get_token(client)
    headers = auth_headers(token)
    lead = client.post("/api/leads", json={}, headers=headers).json()

    workflow = _create_workflow(client, headers)
    _add_node(client, headers, workflow["id"], "action", 0, {"action_type": "generate_ai_response"})

    response = client.post(f"/api/workflows/{workflow['id']}/run", json={"lead_id": lead["id"]}, headers=headers)
    assert "skipped" in response.json()["log"]["steps"][0]["detail"]


def test_generate_summary_action_succeeds_within_a_workflow(client):
    token = register_and_get_token(client)
    headers = auth_headers(token)
    lead = client.post("/api/leads", json={"raw_message": "hi"}, headers=headers).json()

    workflow = _create_workflow(client, headers)
    _add_node(client, headers, workflow["id"], "action", 0, {"action_type": "generate_summary"})

    response = client.post(f"/api/workflows/{workflow['id']}/run", json={"lead_id": lead["id"]}, headers=headers)
    step = response.json()["log"]["steps"][0]
    assert step["status"] == "ok"
    assert step["detail"] == "Conversation summarized"

    conversation = client.get(f"/api/leads/{lead['id']}/conversation", headers=headers).json()
    assert conversation["summary"]


def test_db_node_type_routes_through_action_dispatcher(client):
    token = register_and_get_token(client)
    headers = auth_headers(token)
    lead = client.post("/api/leads", json={"raw_message": "hi"}, headers=headers).json()

    workflow = _create_workflow(client, headers)
    _add_node(client, headers, workflow["id"], "db", 0, {"action_type": "update_lead_status", "value": "contacted"})

    response = client.post(f"/api/workflows/{workflow['id']}/run", json={"lead_id": lead["id"]}, headers=headers)
    assert response.json()["status"] == "success"

    updated = client.get(f"/api/leads/{lead['id']}", headers=headers).json()
    assert updated["status"] == "contacted"


def test_repeat_customer_backfills_missing_name_and_phone(client):
    token = register_and_get_token(client)
    headers = auth_headers(token)
    client.post(
        "/api/leads", json={"raw_message": "first", "customer": {"email": "jane@customerdomain.io"}}, headers=headers
    )
    second = client.post(
        "/api/leads",
        json={
            "raw_message": "second",
            "customer": {"email": "jane@customerdomain.io", "name": "Jane Doe", "phone": "555-1234"},
        },
        headers=headers,
    ).json()

    assert second["customer"]["name"] == "Jane Doe"
    assert second["customer"]["phone"] == "555-1234"


def test_workflow_trigger_swallows_an_engine_level_crash(client, monkeypatch):
    """The outer safety net in workflow_trigger.py — belt-and-suspenders on
    top of the engine's own internal per-node catching, which already makes
    this practically unreachable. Forcing WorkflowEngine.execute itself to
    raise proves lead creation still succeeds even if that inner guarantee
    were ever broken by a future change."""
    from app.workflows.engine import WorkflowEngine

    def broken_execute(self, workflow, lead, business):
        raise RuntimeError("engine-level crash")

    monkeypatch.setattr(WorkflowEngine, "execute", broken_execute)

    token = register_and_get_token(client)
    headers = auth_headers(token)
    client.post("/api/workflows", json={"name": "wf", "trigger_type": "new_enquiry"}, headers=headers)

    response = client.post("/api/leads", json={"raw_message": "hi"}, headers=headers)
    assert response.status_code == 201  # lead creation must survive even this


def test_free_api_provider_reports_configured_when_key_present(monkeypatch):
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
    from app.ai.free_api_provider import FreeAPIProvider, settings as free_api_settings
    from app.ai.gemini_provider import GeminiProvider, settings as gemini_settings
    from app.ai.openai_provider import OpenAIProvider, settings as openai_settings

    monkeypatch.setattr(free_api_settings, "huggingface_api_key", "fake-key-for-test")
    monkeypatch.setattr(gemini_settings, "gemini_api_key", "fake-key-for-test")
    monkeypatch.setattr(openai_settings, "openai_api_key", "fake-key-for-test")

    for provider_cls in [FreeAPIProvider, GeminiProvider, OpenAIProvider]:
        ok, message = provider_cls().check_connection()
        assert ok is True
        assert "configured" in message.lower()
