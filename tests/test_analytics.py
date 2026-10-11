from conftest import auth_headers, register_and_get_token


def test_analytics_overview_requires_auth(client):
    response = client.get("/api/analytics/overview")
    assert response.status_code == 401


def test_analytics_overview_empty_business(client):
    token = register_and_get_token(client)
    response = client.get("/api/analytics/overview", headers=auth_headers(token))
    assert response.status_code == 200
    body = response.json()
    assert body["leads_over_time"] == []
    assert body["leads_by_status"] == []
    assert body["score_distribution"] == {"low": 0, "medium": 0, "high": 0}
    assert body["provider_usage"] == []
    assert body["workflow_performance"] == []


def test_leads_by_status_and_priority(client):
    token = register_and_get_token(client)
    headers = auth_headers(token)
    client.post("/api/leads", json={"raw_message": "Complaint: broken, this is urgent"}, headers=headers)
    client.post("/api/leads", json={"raw_message": "Need info about pricing"}, headers=headers)

    body = client.get("/api/analytics/overview", headers=headers).json()

    status_counts = {c["label"]: c["count"] for c in body["leads_by_status"]}
    assert status_counts.get("new") == 2

    priority_counts = {c["label"]: c["count"] for c in body["leads_by_priority"]}
    assert sum(priority_counts.values()) == 2


def test_leads_by_intent_labels_unclassified(client):
    token = register_and_get_token(client)
    headers = auth_headers(token)
    client.post("/api/leads", json={}, headers=headers)  # no message -> stays unclassified

    body = client.get("/api/analytics/overview", headers=headers).json()
    intent_labels = {c["label"] for c in body["leads_by_intent"]}
    assert "unclassified" in intent_labels


def test_score_distribution_buckets(client):
    token = register_and_get_token(client)
    headers = auth_headers(token)
    # low score: short, no urgency/budget
    client.post("/api/leads", json={"raw_message": "hi"}, headers=headers)
    # high score: quote intent + budget + urgency + large party + longer message
    client.post(
        "/api/leads",
        json={
            "raw_message": "I urgently need a catering quote for a private event with 20 guests, "
            "budget $5000, please help as soon as possible"
        },
        headers=headers,
    )

    body = client.get("/api/analytics/overview", headers=headers).json()
    dist = body["score_distribution"]
    assert dist["low"] + dist["medium"] + dist["high"] == 2
    assert dist["high"] >= 1


def test_provider_usage_tracks_demo_calls(client):
    token = register_and_get_token(client)
    headers = auth_headers(token)
    client.post("/api/leads", json={"raw_message": "hi"}, headers=headers)

    body = client.get("/api/analytics/overview", headers=headers).json()
    usage = {p["provider"]: p for p in body["provider_usage"]}
    assert "demo" in usage
    assert usage["demo"]["total_calls"] >= 3  # classify + extract + score at minimum
    assert usage["demo"]["fallback_calls"] == 0  # demo is the default primary, not a fallback


def test_provider_usage_reflects_fallback(client):
    token = register_and_get_token(client)
    headers = auth_headers(token)
    client.patch("/api/ai/settings", json={"ai_provider": "local", "ai_fallback_provider": "demo"}, headers=headers)
    client.post("/api/leads", json={"raw_message": "hi"}, headers=headers)

    body = client.get("/api/analytics/overview", headers=headers).json()
    usage = {p["provider"]: p for p in body["provider_usage"]}
    assert usage["demo"]["fallback_calls"] >= 1


def test_workflow_performance_counts_executions(client):
    token = register_and_get_token(client)
    headers = auth_headers(token)
    workflow = client.post(
        "/api/workflows", json={"name": "Test", "trigger_type": "new_enquiry"}, headers=headers
    ).json()
    client.post(
        f"/api/workflows/{workflow['id']}/nodes",
        json={"node_type": "action", "order_index": 0, "config": {"action_type": "not_a_real_action"}},
        headers=headers,
    )

    client.post("/api/leads", json={"raw_message": "hi"}, headers=headers)  # triggers a failed execution

    body = client.get("/api/analytics/overview", headers=headers).json()
    perf = next(p for p in body["workflow_performance"] if p["workflow_id"] == workflow["id"])
    assert perf["total_executions"] == 1
    assert perf["failed_count"] == 1
    assert perf["success_count"] == 0


def test_workflow_with_no_executions_is_omitted(client):
    token = register_and_get_token(client)
    headers = auth_headers(token)
    client.post("/api/workflows", json={"name": "Unused", "trigger_type": "manual"}, headers=headers)

    body = client.get("/api/analytics/overview", headers=headers).json()
    assert body["workflow_performance"] == []


def test_analytics_isolated_per_business(client):
    token_a = register_and_get_token(client, email="ownera@techfixsolutions.io", business_name="Biz A")
    token_b = register_and_get_token(client, email="ownerb@techfixsolutions.io", business_name="Biz B")
    client.post("/api/leads", json={"raw_message": "hi"}, headers=auth_headers(token_a))

    body_b = client.get("/api/analytics/overview", headers=auth_headers(token_b)).json()
    assert body_b["leads_by_status"] == []
