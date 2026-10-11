from conftest import auth_headers, register_and_get_token

from app.models.notification import Notification
from app.models.task import Task


def _create_workflow(client, headers, trigger_type="manual", is_active=True, name="Test Workflow"):
    return client.post(
        "/api/workflows",
        json={"name": name, "trigger_type": trigger_type, "is_active": is_active},
        headers=headers,
    ).json()


def _add_node(client, headers, workflow_id, node_type, order_index, config=None):
    return client.post(
        f"/api/workflows/{workflow_id}/nodes",
        json={"node_type": node_type, "order_index": order_index, "config": config},
        headers=headers,
    ).json()


# ---- CRUD ----------------------------------------------------------------


def test_create_and_get_workflow(client):
    token = register_and_get_token(client)
    headers = auth_headers(token)
    workflow = _create_workflow(client, headers)
    assert workflow["trigger_type"] == "manual"
    assert workflow["is_active"] is True
    assert workflow["nodes"] == []

    fetched = client.get(f"/api/workflows/{workflow['id']}", headers=headers)
    assert fetched.status_code == 200


def test_workflow_isolated_per_business(client):
    token_a = register_and_get_token(client, email="ownera@techfixsolutions.io", business_name="Biz A")
    token_b = register_and_get_token(client, email="ownerb@techfixsolutions.io", business_name="Biz B")

    workflow = _create_workflow(client, auth_headers(token_a))
    response = client.get(f"/api/workflows/{workflow['id']}", headers=auth_headers(token_b))
    assert response.status_code == 404


def test_update_and_delete_workflow(client):
    token = register_and_get_token(client)
    headers = auth_headers(token)
    workflow = _create_workflow(client, headers)

    update_response = client.patch(f"/api/workflows/{workflow['id']}", json={"is_active": False}, headers=headers)
    assert update_response.json()["is_active"] is False

    delete_response = client.delete(f"/api/workflows/{workflow['id']}", headers=headers)
    assert delete_response.status_code == 204
    assert client.get(f"/api/workflows/{workflow['id']}", headers=headers).status_code == 404


def test_node_crud(client):
    token = register_and_get_token(client)
    headers = auth_headers(token)
    workflow = _create_workflow(client, headers)

    node = _add_node(client, headers, workflow["id"], "action", 0, {"action_type": "log_execution"})
    assert node["node_type"] == "action"

    update_response = client.patch(
        f"/api/workflows/{workflow['id']}/nodes/{node['id']}", json={"order_index": 5}, headers=headers
    )
    assert update_response.json()["order_index"] == 5

    delete_response = client.delete(f"/api/workflows/{workflow['id']}/nodes/{node['id']}", headers=headers)
    assert delete_response.status_code == 204


def test_node_operations_require_auth(client):
    token = register_and_get_token(client)
    workflow = _create_workflow(client, auth_headers(token))
    response = client.post(f"/api/workflows/{workflow['id']}/nodes", json={"node_type": "action"})
    assert response.status_code == 401


# ---- manual run + condition gating ----------------------------------------


def test_condition_met_runs_action(client):
    token = register_and_get_token(client)
    headers = auth_headers(token)
    lead = client.post(
        "/api/leads",
        json={"raw_message": "I urgently need a quote, budget $5000"},  # scores high
        headers=headers,
    ).json()
    assert lead["score"] > 50

    workflow = _create_workflow(client, headers)
    _add_node(client, headers, workflow["id"], "trigger", 0)
    _add_node(client, headers, workflow["id"], "condition", 1, {"field": "score", "operator": "gt", "value": 50})
    _add_node(client, headers, workflow["id"], "action", 2, {"action_type": "set_priority", "value": "high"})
    _add_node(client, headers, workflow["id"], "end", 3)

    run_response = client.post(f"/api/workflows/{workflow['id']}/run", json={"lead_id": lead["id"]}, headers=headers)
    assert run_response.status_code == 200
    execution = run_response.json()
    assert execution["status"] == "success"
    step_types = [s["node_type"] for s in execution["log"]["steps"]]
    assert step_types == ["trigger", "condition", "action", "end"]

    updated_lead = client.get(f"/api/leads/{lead['id']}", headers=headers).json()
    assert updated_lead["priority"] == "high"


def test_condition_not_met_halts_and_skips_remaining_nodes(client):
    token = register_and_get_token(client)
    headers = auth_headers(token)
    lead = client.post("/api/leads", json={"raw_message": "just saying hi"}, headers=headers).json()
    assert lead["score"] < 50

    workflow = _create_workflow(client, headers)
    _add_node(client, headers, workflow["id"], "condition", 0, {"field": "score", "operator": "gt", "value": 50})
    _add_node(client, headers, workflow["id"], "action", 1, {"action_type": "set_priority", "value": "high"})

    run_response = client.post(f"/api/workflows/{workflow['id']}/run", json={"lead_id": lead["id"]}, headers=headers)
    execution = run_response.json()
    assert execution["status"] == "success"  # halting is not a failure
    step_types = [s["node_type"] for s in execution["log"]["steps"]]
    assert step_types == ["condition"]  # action node never ran

    updated_lead = client.get(f"/api/leads/{lead['id']}", headers=headers).json()
    assert updated_lead["priority"] == "normal"


def test_intent_complaint_sets_high_priority(client):
    """Mirrors the CLAUDE.md example condition literally."""
    token = register_and_get_token(client)
    headers = auth_headers(token)
    lead = client.post(
        "/api/leads", json={"raw_message": "This is a complaint, the app is broken and not working"}, headers=headers
    ).json()
    assert lead["intent"] == "complaint"

    workflow = _create_workflow(client, headers)
    _add_node(client, headers, workflow["id"], "condition", 0, {"field": "intent", "operator": "eq", "value": "complaint"})
    _add_node(client, headers, workflow["id"], "action", 1, {"action_type": "set_priority", "value": "high"})

    client.post(f"/api/workflows/{workflow['id']}/run", json={"lead_id": lead["id"]}, headers=headers)
    updated_lead = client.get(f"/api/leads/{lead['id']}", headers=headers).json()
    assert updated_lead["priority"] == "high"


def test_run_workflow_requires_ownership(client):
    token_a = register_and_get_token(client, email="ownera@techfixsolutions.io", business_name="Biz A")
    token_b = register_and_get_token(client, email="ownerb@techfixsolutions.io", business_name="Biz B")

    lead = client.post("/api/leads", json={"raw_message": "hi"}, headers=auth_headers(token_a)).json()
    workflow = _create_workflow(client, auth_headers(token_b))

    response = client.post(
        f"/api/workflows/{workflow['id']}/run", json={"lead_id": lead["id"]}, headers=auth_headers(token_b)
    )
    assert response.status_code == 404  # lead not visible from Biz B


# ---- action node coverage --------------------------------------------------


def test_action_create_notification(client):
    token = register_and_get_token(client)
    headers = auth_headers(token)
    lead = client.post("/api/leads", json={"raw_message": "hi"}, headers=headers).json()
    workflow = _create_workflow(client, headers)
    _add_node(
        client, headers, workflow["id"], "notification", 0,
        {"message": "New lead needs attention", "notification_type": "high_priority_lead"},
    )
    client.post(f"/api/workflows/{workflow['id']}/run", json={"lead_id": lead["id"]}, headers=headers)

    session = client.test_session_factory()
    try:
        notifications = session.query(Notification).all()
    finally:
        session.close()
    assert any(n.message == "New lead needs attention" for n in notifications)


def test_action_add_task(client):
    token = register_and_get_token(client)
    headers = auth_headers(token)
    lead = client.post("/api/leads", json={"raw_message": "hi"}, headers=headers).json()
    workflow = _create_workflow(client, headers)
    _add_node(client, headers, workflow["id"], "action", 0, {"action_type": "add_task", "title": "Call the lead back"})
    client.post(f"/api/workflows/{workflow['id']}/run", json={"lead_id": lead["id"]}, headers=headers)

    session = client.test_session_factory()
    try:
        tasks = session.query(Task).filter(Task.lead_id == lead["id"]).all()
    finally:
        session.close()
    assert any(t.title == "Call the lead back" for t in tasks)


def test_action_send_email_is_simulated_only(client):
    token = register_and_get_token(client)
    headers = auth_headers(token)
    lead = client.post(
        "/api/leads", json={"raw_message": "hi", "customer": {"email": "jane@customerdomain.io"}}, headers=headers
    ).json()
    workflow = _create_workflow(client, headers)
    _add_node(client, headers, workflow["id"], "action", 0, {"action_type": "send_email", "subject": "Thanks!"})

    run_response = client.post(
        f"/api/workflows/{workflow['id']}/run", json={"lead_id": lead["id"]}, headers=headers
    )
    detail = run_response.json()["log"]["steps"][0]["detail"]
    assert "[SIMULATED]" in detail
    assert "jane@customerdomain.io" in detail


def test_action_generate_ai_response(client):
    token = register_and_get_token(client)
    headers = auth_headers(token)
    lead = client.post("/api/leads", json={"raw_message": "Need a quote for a website"}, headers=headers).json()
    workflow = _create_workflow(client, headers)
    _add_node(client, headers, workflow["id"], "action", 0, {"action_type": "generate_ai_response"})

    client.post(f"/api/workflows/{workflow['id']}/run", json={"lead_id": lead["id"]}, headers=headers)

    conversation = client.get(f"/api/leads/{lead['id']}/conversation", headers=headers).json()
    assert any(m["sender"] == "ai" for m in conversation["messages"])


def test_unknown_action_type_marks_execution_failed_but_does_not_crash(client):
    token = register_and_get_token(client)
    headers = auth_headers(token)
    lead = client.post("/api/leads", json={"raw_message": "hi"}, headers=headers).json()
    workflow = _create_workflow(client, headers)
    _add_node(client, headers, workflow["id"], "action", 0, {"action_type": "not_a_real_action"})

    response = client.post(f"/api/workflows/{workflow['id']}/run", json={"lead_id": lead["id"]}, headers=headers)
    assert response.status_code == 200  # engine failure must not become an HTTP error
    assert response.json()["status"] == "failed"


# ---- auto-triggering on lead creation --------------------------------------


def test_new_enquiry_workflow_autofires_on_lead_creation(client):
    token = register_and_get_token(client)
    headers = auth_headers(token)

    workflow = _create_workflow(client, headers, trigger_type="new_enquiry")
    _add_node(client, headers, workflow["id"], "condition", 0, {"field": "intent", "operator": "eq", "value": "complaint"})
    _add_node(client, headers, workflow["id"], "action", 1, {"action_type": "set_priority", "value": "high"})

    lead = client.post(
        "/api/leads", json={"raw_message": "Complaint: this is broken and not working"}, headers=headers
    ).json()
    assert lead["priority"] == "high"  # set automatically, no manual /run call


def test_inactive_workflow_does_not_autofire(client):
    token = register_and_get_token(client)
    headers = auth_headers(token)

    workflow = _create_workflow(client, headers, trigger_type="new_enquiry", is_active=False)
    _add_node(client, headers, workflow["id"], "action", 0, {"action_type": "set_priority", "value": "high"})

    lead = client.post("/api/leads", json={"raw_message": "hi"}, headers=headers).json()
    assert lead["priority"] == "normal"


def test_new_customer_workflow_fires_only_on_first_lead_from_that_customer(client):
    token = register_and_get_token(client)
    headers = auth_headers(token)

    workflow = _create_workflow(client, headers, trigger_type="new_customer")
    _add_node(client, headers, workflow["id"], "action", 0, {"action_type": "add_task", "title": "Welcome new customer"})

    client.post(
        "/api/leads",
        json={"raw_message": "hi", "customer": {"email": "first@customerdomain.io"}},
        headers=headers,
    )
    client.post(
        "/api/leads",
        json={"raw_message": "hi again", "customer": {"email": "first@customerdomain.io"}},
        headers=headers,
    )

    session = client.test_session_factory()
    try:
        welcome_tasks = session.query(Task).filter(Task.title == "Welcome new customer").all()
    finally:
        session.close()
    assert len(welcome_tasks) == 1  # only fired for the first, genuinely-new customer


def test_execution_history_is_listed(client):
    token = register_and_get_token(client)
    headers = auth_headers(token)
    lead = client.post("/api/leads", json={"raw_message": "hi"}, headers=headers).json()
    workflow = _create_workflow(client, headers)
    _add_node(client, headers, workflow["id"], "end", 0)

    client.post(f"/api/workflows/{workflow['id']}/run", json={"lead_id": lead["id"]}, headers=headers)
    client.post(f"/api/workflows/{workflow['id']}/run", json={"lead_id": lead["id"]}, headers=headers)

    response = client.get(f"/api/workflows/{workflow['id']}/executions", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) == 2
