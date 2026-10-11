import pytest
from conftest import auth_headers, register_and_get_token

from app.ai.base import ExtractedInfo, GeneratedResponse, IntentClassification, LeadScoreResult, SummaryResult
from app.ai.local_provider import LocalProvider
from app.ai.mock_provider import MockProvider
from app.ai.service import AIService, AllProvidersFailedError
from app.ai.validation import InvalidAIOutputError, validate_result
from app.models.ai_log import AILog
from app.models.business import Business
from app.models.workflow import WorkflowNode
from app.workflows import nodes as workflow_nodes


def _break_classify(monkeypatch, message="simulated provider crash"):
    def broken(self, text):
        raise RuntimeError(message)

    monkeypatch.setattr(MockProvider, "classify_intent", broken)


def _break_generate_response(monkeypatch, message="simulated provider crash"):
    def broken(self, business_profile, text, extracted):
        raise RuntimeError(message)

    monkeypatch.setattr(MockProvider, "generate_response", broken)


def _break_summarize(monkeypatch, message="simulated provider crash"):
    def broken(self, messages):
        raise RuntimeError(message)

    monkeypatch.setattr(MockProvider, "summarize", broken)


# ---- the fallback chain must catch ANY exception, not just AIProviderError ----


def test_ai_service_raises_all_providers_failed_and_logs_it(client, monkeypatch):
    token = register_and_get_token(client)
    _break_classify(monkeypatch)

    session = client.test_session_factory()
    try:
        business = session.query(Business).first()
        service = AIService(session)

        with pytest.raises(AllProvidersFailedError):
            service.classify_intent(business, "hello")

        logs = session.query(AILog).filter(AILog.success.is_(False)).all()
        assert len(logs) == 1
        assert "simulated provider crash" in logs[0].error_message
    finally:
        session.close()


def test_lead_creation_still_succeeds_when_every_provider_crashes(client, monkeypatch):
    """The most important guarantee in the whole app: a totally broken AI
    layer must never stop a lead from being saved."""
    token = register_and_get_token(client)
    _break_classify(monkeypatch)

    response = client.post("/api/leads", json={"raw_message": "hi"}, headers=auth_headers(token))
    assert response.status_code == 201
    body = response.json()
    assert body["intent"] is None
    assert body["score"] is None


def test_reclassify_endpoint_returns_502_not_500_when_providers_crash(client, monkeypatch):
    token = register_and_get_token(client)
    headers = auth_headers(token)
    lead = client.post("/api/leads", json={"raw_message": "hi"}, headers=headers).json()
    assert lead["intent"] is not None  # classified fine before we break anything

    _break_classify(monkeypatch)
    response = client.post(f"/api/leads/{lead['id']}/classify", headers=headers)
    assert response.status_code == 502


def test_generate_response_returns_502_not_500_when_providers_crash(client, monkeypatch):
    token = register_and_get_token(client)
    headers = auth_headers(token)
    lead = client.post("/api/leads", json={"raw_message": "hi"}, headers=headers).json()

    _break_generate_response(monkeypatch)
    response = client.post(f"/api/leads/{lead['id']}/generate-response", headers=headers)
    assert response.status_code == 502


def test_summarize_returns_502_not_500_when_providers_crash(client, monkeypatch):
    token = register_and_get_token(client)
    headers = auth_headers(token)
    lead = client.post("/api/leads", json={"raw_message": "hi"}, headers=headers).json()

    _break_summarize(monkeypatch)
    response = client.post(f"/api/leads/{lead['id']}/summarize", headers=headers)
    assert response.status_code == 502


# ---- the workflow engine must catch node-level failures the same way ----


def test_ai_processor_node_fails_cleanly_when_providers_crash(client, monkeypatch):
    token = register_and_get_token(client)
    headers = auth_headers(token)
    workflow = client.post("/api/workflows", json={"name": "wf", "trigger_type": "manual"}, headers=headers).json()
    client.post(
        f"/api/workflows/{workflow['id']}/nodes",
        json={"node_type": "ai_processor", "order_index": 0, "config": {"force": True}},
        headers=headers,
    )
    lead = client.post("/api/leads", json={"raw_message": "hi"}, headers=headers).json()

    _break_classify(monkeypatch)
    run_response = client.post(f"/api/workflows/{workflow['id']}/run", json={"lead_id": lead["id"]}, headers=headers)
    assert run_response.status_code == 200  # engine failure must not become an HTTP error
    execution = run_response.json()
    assert execution["status"] == "failed"
    assert execution["log"]["steps"][0]["status"] == "failed"


def test_generate_ai_response_action_fails_cleanly_when_providers_crash(client, monkeypatch):
    token = register_and_get_token(client)
    headers = auth_headers(token)
    workflow = client.post("/api/workflows", json={"name": "wf", "trigger_type": "manual"}, headers=headers).json()
    client.post(
        f"/api/workflows/{workflow['id']}/nodes",
        json={"node_type": "action", "order_index": 0, "config": {"action_type": "generate_ai_response"}},
        headers=headers,
    )
    lead = client.post("/api/leads", json={"raw_message": "hi"}, headers=headers).json()

    _break_generate_response(monkeypatch)
    run_response = client.post(f"/api/workflows/{workflow['id']}/run", json={"lead_id": lead["id"]}, headers=headers)
    assert run_response.json()["status"] == "failed"


def test_generate_summary_action_fails_cleanly_when_providers_crash(client, monkeypatch):
    token = register_and_get_token(client)
    headers = auth_headers(token)
    workflow = client.post("/api/workflows", json={"name": "wf", "trigger_type": "manual"}, headers=headers).json()
    client.post(
        f"/api/workflows/{workflow['id']}/nodes",
        json={"node_type": "action", "order_index": 0, "config": {"action_type": "generate_summary"}},
        headers=headers,
    )
    lead = client.post("/api/leads", json={"raw_message": "hi"}, headers=headers).json()

    _break_summarize(monkeypatch)
    run_response = client.post(f"/api/workflows/{workflow['id']}/run", json={"lead_id": lead["id"]}, headers=headers)
    assert run_response.json()["status"] == "failed"


def test_unknown_node_type_is_skipped_not_crashed(client):
    """node_type is constrained by the API schema, so an unknown type can
    only reach the engine via direct data manipulation — worth proving the
    engine still handles it gracefully rather than assuming the schema is
    the only line of defense."""
    token = register_and_get_token(client)
    headers = auth_headers(token)
    workflow = client.post("/api/workflows", json={"name": "wf", "trigger_type": "manual"}, headers=headers).json()
    lead = client.post("/api/leads", json={"raw_message": "hi"}, headers=headers).json()

    session = client.test_session_factory()
    try:
        session.add(WorkflowNode(workflow_id=workflow["id"], node_type="totally_made_up", order_index=0))
        session.commit()
    finally:
        session.close()

    run_response = client.post(f"/api/workflows/{workflow['id']}/run", json={"lead_id": lead["id"]}, headers=headers)
    assert run_response.status_code == 200
    execution = run_response.json()
    assert execution["status"] == "success"  # an unknown node is skipped, not a failure
    assert execution["log"]["steps"][0]["status"] == "skipped"


def test_node_handler_raising_a_bare_exception_fails_cleanly(client, monkeypatch):
    def broken_handler(db, business, lead, config):
        raise ValueError("a bug in a node handler")

    monkeypatch.setitem(workflow_nodes.NODE_HANDLERS, "trigger", broken_handler)

    token = register_and_get_token(client)
    headers = auth_headers(token)
    workflow = client.post("/api/workflows", json={"name": "wf", "trigger_type": "manual"}, headers=headers).json()
    client.post(f"/api/workflows/{workflow['id']}/nodes", json={"node_type": "trigger", "order_index": 0}, headers=headers)
    lead = client.post("/api/leads", json={"raw_message": "hi"}, headers=headers).json()

    run_response = client.post(f"/api/workflows/{workflow['id']}/run", json={"lead_id": lead["id"]}, headers=headers)
    assert run_response.status_code == 200
    execution = run_response.json()
    assert execution["status"] == "failed"
    assert "Unhandled error" in execution["log"]["steps"][0]["detail"]


# ---- a provider that returns garbage is treated like one that failed ----


def _use_local_then_demo(client, token):
    response = client.patch(
        "/api/ai/settings", json={"ai_provider": "local", "ai_fallback_provider": "demo"}, headers=auth_headers(token)
    )
    assert response.status_code == 200


def test_invalid_provider_output_falls_back_instead_of_being_saved(client, monkeypatch):
    token = register_and_get_token(client)
    _use_local_then_demo(client, token)

    def garbage(self, text):
        return IntentClassification(intent="definitely_not_an_intent", category=None, confidence=7.5)

    monkeypatch.setattr(LocalProvider, "classify_intent", garbage)

    session = client.test_session_factory()
    try:
        business = session.query(Business).first()
        result, provider_used, fallback_used, reason = AIService(session).classify_intent(business, "book a table")
    finally:
        session.close()

    assert provider_used == "demo"
    assert fallback_used is True
    assert "invalid output" in reason
    assert result.intent == "booking_request"


def test_every_failed_attempt_gets_its_own_log_row(client):
    token = register_and_get_token(client)
    _use_local_then_demo(client, token)

    session = client.test_session_factory()
    try:
        business = session.query(Business).first()
        AIService(session).classify_intent(business, "book a table")
        logs = session.query(AILog).filter(AILog.operation == "classify").order_by(AILog.id).all()
    finally:
        session.close()

    assert [(log.actual_provider, log.success) for log in logs] == [("local", False), ("demo", True)]
    assert "local" in logs[0].error_message
    assert logs[0].fallback_reason is None  # it was the first provider tried
    assert logs[1].fallback_used is True
    assert logs[1].fallback_reason == logs[0].error_message


@pytest.mark.parametrize(
    "result",
    [
        IntentClassification(intent="booking_request", category="not_a_category", confidence=0.9),
        IntentClassification(intent="booking_request", category=None, confidence="high"),
        ExtractedInfo(urgency="extremely"),
        ExtractedInfo(email=["a@b.io"]),
        LeadScoreResult(score=250),
        LeadScoreResult(score=True),
        GeneratedResponse(text="   "),
        SummaryResult(summary=None),
        "just a string",
    ],
)
def test_validate_result_rejects_unusable_output(result):
    with pytest.raises(InvalidAIOutputError):
        validate_result(result)
