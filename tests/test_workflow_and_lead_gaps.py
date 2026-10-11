from conftest import auth_headers, register_and_get_token

from app.models.workflow import WorkflowExecution, WorkflowNode


def _create_workflow(client, headers):
    return client.post("/api/workflows", json={"name": "wf", "trigger_type": "manual"}, headers=headers).json()


def _add_node(client, headers, workflow_id, node_type, order_index, config=None):
    return client.post(
        f"/api/workflows/{workflow_id}/nodes",
        json={"node_type": node_type, "order_index": order_index, "config": config},
        headers=headers,
    ).json()


def test_action_update_lead_status(client):
    token = register_and_get_token(client)
    headers = auth_headers(token)
    lead = client.post("/api/leads", json={"raw_message": "hi"}, headers=headers).json()
    workflow = _create_workflow(client, headers)
    _add_node(client, headers, workflow["id"], "action", 0, {"action_type": "update_lead_status", "value": "qualified"})

    client.post(f"/api/workflows/{workflow['id']}/run", json={"lead_id": lead["id"]}, headers=headers)
    updated = client.get(f"/api/leads/{lead['id']}", headers=headers).json()
    assert updated["status"] == "qualified"


def test_action_save_lead_is_a_no_op_that_succeeds(client):
    token = register_and_get_token(client)
    headers = auth_headers(token)
    lead = client.post("/api/leads", json={"raw_message": "hi"}, headers=headers).json()
    workflow = _create_workflow(client, headers)
    _add_node(client, headers, workflow["id"], "action", 0, {"action_type": "save_lead"})

    response = client.post(f"/api/workflows/{workflow['id']}/run", json={"lead_id": lead["id"]}, headers=headers)
    assert response.json()["status"] == "success"


def test_action_send_messenger_reply_is_simulated_only(client):
    token = register_and_get_token(client)
    headers = auth_headers(token)
    lead = client.post(
        "/api/channels/messenger/simulate", json={"sender_id": "psid-9", "text": "hi"}, headers=headers
    ).json()
    workflow = _create_workflow(client, headers)
    _add_node(client, headers, workflow["id"], "action", 0, {"action_type": "send_messenger_reply", "message": "Thanks!"})

    response = client.post(f"/api/workflows/{workflow['id']}/run", json={"lead_id": lead["id"]}, headers=headers)
    detail = response.json()["log"]["steps"][0]["detail"]
    assert "[SIMULATED]" in detail
    assert "psid-9" in detail


def test_action_log_execution(client):
    token = register_and_get_token(client)
    headers = auth_headers(token)
    lead = client.post("/api/leads", json={"raw_message": "hi"}, headers=headers).json()
    workflow = _create_workflow(client, headers)
    _add_node(client, headers, workflow["id"], "action", 0, {"action_type": "log_execution", "message": "custom log line"})

    response = client.post(f"/api/workflows/{workflow['id']}/run", json={"lead_id": lead["id"]}, headers=headers)
    assert response.json()["log"]["steps"][0]["detail"] == "custom log line"


def test_condition_type_mismatch_fails_gracefully(client):
    token = register_and_get_token(client)
    headers = auth_headers(token)
    lead = client.post("/api/leads", json={"raw_message": "hi"}, headers=headers).json()
    workflow = _create_workflow(client, headers)
    # score is an int; comparing with "gt" against a string raises TypeError internally
    _add_node(client, headers, workflow["id"], "condition", 0, {"field": "score", "operator": "gt", "value": "not-a-number"})

    response = client.post(f"/api/workflows/{workflow['id']}/run", json={"lead_id": lead["id"]}, headers=headers)
    assert response.status_code == 200  # must not become a 500
    assert response.json()["status"] == "failed"


def test_deleting_workflow_cascades_to_nodes_and_executions(client):
    token = register_and_get_token(client)
    headers = auth_headers(token)
    lead = client.post("/api/leads", json={"raw_message": "hi"}, headers=headers).json()
    workflow = _create_workflow(client, headers)
    _add_node(client, headers, workflow["id"], "end", 0)
    client.post(f"/api/workflows/{workflow['id']}/run", json={"lead_id": lead["id"]}, headers=headers)

    client.delete(f"/api/workflows/{workflow['id']}", headers=headers)

    session = client.test_session_factory()
    try:
        remaining_nodes = session.query(WorkflowNode).filter(WorkflowNode.workflow_id == workflow["id"]).count()
        remaining_executions = (
            session.query(WorkflowExecution).filter(WorkflowExecution.workflow_id == workflow["id"]).count()
        )
    finally:
        session.close()

    assert remaining_nodes == 0
    assert remaining_executions == 0


def test_filter_leads_by_priority(client):
    token = register_and_get_token(client)
    headers = auth_headers(token)
    lead1 = client.post("/api/leads", json={"raw_message": "one"}, headers=headers).json()
    client.post("/api/leads", json={"raw_message": "two"}, headers=headers)
    client.patch(f"/api/leads/{lead1['id']}", json={"priority": "high"}, headers=headers)

    response = client.get("/api/leads?priority=high", headers=headers)
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == lead1["id"]
