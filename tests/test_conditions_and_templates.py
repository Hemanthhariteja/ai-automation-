from conftest import auth_headers, register_and_get_token


def _create_workflow(client, headers, trigger_type="manual"):
    return client.post(
        "/api/workflows", json={"name": "Test", "trigger_type": trigger_type}, headers=headers
    ).json()


def _add_node(client, headers, workflow_id, node_type, order_index, config=None):
    return client.post(
        f"/api/workflows/{workflow_id}/nodes",
        json={"node_type": node_type, "order_index": order_index, "config": config},
        headers=headers,
    ).json()


# ---- compound conditions ---------------------------------------------------


def test_compound_all_requires_every_clause(client):
    token = register_and_get_token(client)
    headers = auth_headers(token)
    lead = client.post(
        "/api/leads", json={"raw_message": "urgent, need a quote, budget $2000"}, headers=headers
    ).json()
    assert lead["extracted_data"]["urgency"] == "high"
    assert lead["extracted_data"]["budget"] is not None

    workflow = _create_workflow(client, headers)
    _add_node(
        client, headers, workflow["id"], "condition", 0,
        {
            "logic": "all",
            "clauses": [
                {"field": "extracted_data.urgency", "operator": "eq", "value": "high"},
                {"field": "extracted_data.budget", "operator": "neq", "value": None},
            ],
        },
    )
    _add_node(client, headers, workflow["id"], "action", 1, {"action_type": "set_priority", "value": "high"})

    client.post(f"/api/workflows/{workflow['id']}/run", json={"lead_id": lead["id"]}, headers=headers)
    updated = client.get(f"/api/leads/{lead['id']}", headers=headers).json()
    assert updated["priority"] == "high"


def test_compound_all_fails_if_one_clause_fails(client):
    token = register_and_get_token(client)
    headers = auth_headers(token)
    # urgent but no budget mentioned
    lead = client.post("/api/leads", json={"raw_message": "this is urgent, please help"}, headers=headers).json()
    assert lead["extracted_data"]["budget"] is None

    workflow = _create_workflow(client, headers)
    _add_node(
        client, headers, workflow["id"], "condition", 0,
        {
            "logic": "all",
            "clauses": [
                {"field": "extracted_data.urgency", "operator": "eq", "value": "high"},
                {"field": "extracted_data.budget", "operator": "neq", "value": None},
            ],
        },
    )
    _add_node(client, headers, workflow["id"], "action", 1, {"action_type": "set_priority", "value": "high"})

    run_response = client.post(f"/api/workflows/{workflow['id']}/run", json={"lead_id": lead["id"]}, headers=headers)
    assert run_response.json()["status"] == "success"  # halt, not failure
    updated = client.get(f"/api/leads/{lead['id']}", headers=headers).json()
    assert updated["priority"] == "normal"


def test_compound_any_passes_if_one_clause_matches(client):
    token = register_and_get_token(client)
    headers = auth_headers(token)
    lead = client.post("/api/leads", json={"raw_message": "please help, this is urgent"}, headers=headers).json()

    workflow = _create_workflow(client, headers)
    _add_node(
        client, headers, workflow["id"], "condition", 0,
        {
            "logic": "any",
            "clauses": [
                {"field": "extracted_data.urgency", "operator": "eq", "value": "high"},
                {"field": "intent", "operator": "eq", "value": "quote_request"},
            ],
        },
    )
    _add_node(client, headers, workflow["id"], "action", 1, {"action_type": "set_priority", "value": "high"})

    client.post(f"/api/workflows/{workflow['id']}/run", json={"lead_id": lead["id"]}, headers=headers)
    updated = client.get(f"/api/leads/{lead['id']}", headers=headers).json()
    assert updated["priority"] == "high"


def test_invalid_compound_condition_fails_gracefully(client):
    token = register_and_get_token(client)
    headers = auth_headers(token)
    lead = client.post("/api/leads", json={"raw_message": "hi"}, headers=headers).json()

    workflow = _create_workflow(client, headers)
    _add_node(client, headers, workflow["id"], "condition", 0, {"logic": "xor", "clauses": []})

    response = client.post(f"/api/workflows/{workflow['id']}/run", json={"lead_id": lead["id"]}, headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "failed"


# ---- condition preview endpoint --------------------------------------------


def test_evaluate_condition_preview_does_not_mutate_lead(client):
    token = register_and_get_token(client)
    headers = auth_headers(token)
    lead = client.post("/api/leads", json={"raw_message": "hi"}, headers=headers).json()

    response = client.post(
        "/api/workflows/evaluate-condition",
        json={"lead_id": lead["id"], "config": {"field": "status", "operator": "eq", "value": "new"}},
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["passed"] is True

    unchanged = client.get(f"/api/leads/{lead['id']}", headers=headers).json()
    assert unchanged["status"] == "new"  # preview never touched the lead


def test_evaluate_condition_preview_requires_ownership(client):
    token_a = register_and_get_token(client, email="ownera@techfixsolutions.io", business_name="Biz A")
    token_b = register_and_get_token(client, email="ownerb@techfixsolutions.io", business_name="Biz B")
    lead = client.post("/api/leads", json={"raw_message": "hi"}, headers=auth_headers(token_a)).json()

    response = client.post(
        "/api/workflows/evaluate-condition",
        json={"lead_id": lead["id"], "config": {"field": "status", "operator": "eq", "value": "new"}},
        headers=auth_headers(token_b),
    )
    assert response.status_code == 404


def test_evaluate_condition_preview_rejects_bad_config(client):
    token = register_and_get_token(client)
    headers = auth_headers(token)
    lead = client.post("/api/leads", json={"raw_message": "hi"}, headers=headers).json()

    response = client.post(
        "/api/workflows/evaluate-condition",
        json={"lead_id": lead["id"], "config": {"field": "status", "operator": "not_a_real_operator", "value": "new"}},
        headers=headers,
    )
    assert response.status_code == 400


# ---- rule templates ---------------------------------------------------------


def test_list_templates(client):
    token = register_and_get_token(client)
    response = client.get("/api/workflows/templates", headers=auth_headers(token))
    assert response.status_code == 200
    ids = {t["id"] for t in response.json()}
    assert {"high_score_alert", "complaint_priority", "auto_respond_and_followup", "urgent_and_high_budget"} <= ids


def test_instantiate_template_creates_working_workflow(client):
    token = register_and_get_token(client)
    headers = auth_headers(token)

    create_response = client.post("/api/workflows/templates/complaint_priority", headers=headers)
    assert create_response.status_code == 201
    workflow = create_response.json()
    assert workflow["trigger_type"] == "new_enquiry"
    assert len(workflow["nodes"]) == 5

    # prove it's a real, functioning workflow, not just a structural copy
    lead = client.post(
        "/api/leads", json={"raw_message": "Complaint: this is broken and not working"}, headers=headers
    ).json()
    assert lead["priority"] == "high"  # fired automatically via new_enquiry trigger


def test_instantiate_unknown_template_404s(client):
    token = register_and_get_token(client)
    response = client.post("/api/workflows/templates/not_a_real_template", headers=auth_headers(token))
    assert response.status_code == 404


def test_instantiated_template_is_independently_editable(client):
    """Proves templates are additive starting points, not a special
    mechanism — the resulting workflow can be edited like any other."""
    token = register_and_get_token(client)
    headers = auth_headers(token)
    workflow = client.post("/api/workflows/templates/high_score_alert", headers=headers).json()

    update_response = client.patch(f"/api/workflows/{workflow['id']}", json={"is_active": False}, headers=headers)
    assert update_response.status_code == 200
    assert update_response.json()["is_active"] is False
