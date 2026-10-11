from conftest import auth_headers, register_and_get_token


def _create_workflow_with_notification_and_task(client, headers):
    workflow = client.post(
        "/api/workflows", json={"name": "Notifier", "trigger_type": "new_enquiry"}, headers=headers
    ).json()
    client.post(
        f"/api/workflows/{workflow['id']}/nodes",
        json={"node_type": "notification", "order_index": 0, "config": {"message": "New lead arrived"}},
        headers=headers,
    )
    client.post(
        f"/api/workflows/{workflow['id']}/nodes",
        json={"node_type": "action", "order_index": 1, "config": {"action_type": "add_task", "title": "Follow up"}},
        headers=headers,
    )
    return workflow


# ---- notifications ----------------------------------------------------------


def test_list_notifications_and_unread_count(client):
    token = register_and_get_token(client)
    headers = auth_headers(token)
    _create_workflow_with_notification_and_task(client, headers)
    client.post("/api/leads", json={"raw_message": "hi"}, headers=headers)

    response = client.get("/api/notifications", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["unread_count"] == 1
    assert body["items"][0]["message"] == "New lead arrived"


def test_mark_notification_read(client):
    token = register_and_get_token(client)
    headers = auth_headers(token)
    _create_workflow_with_notification_and_task(client, headers)
    client.post("/api/leads", json={"raw_message": "hi"}, headers=headers)

    notification_id = client.get("/api/notifications", headers=headers).json()["items"][0]["id"]
    response = client.patch(f"/api/notifications/{notification_id}", json={"is_read": True}, headers=headers)
    assert response.status_code == 200
    assert response.json()["is_read"] is True

    unread = client.get("/api/notifications?unread_only=true", headers=headers).json()
    assert unread["total"] == 0


def test_notifications_isolated_per_business(client):
    token_a = register_and_get_token(client, email="ownera@techfixsolutions.io", business_name="Biz A")
    token_b = register_and_get_token(client, email="ownerb@techfixsolutions.io", business_name="Biz B")
    _create_workflow_with_notification_and_task(client, auth_headers(token_a))
    client.post("/api/leads", json={"raw_message": "hi"}, headers=auth_headers(token_a))

    response_b = client.get("/api/notifications", headers=auth_headers(token_b))
    assert response_b.json()["total"] == 0


def test_notifications_require_auth(client):
    response = client.get("/api/notifications")
    assert response.status_code == 401


# ---- tasks --------------------------------------------------------------------


def test_list_tasks(client):
    token = register_and_get_token(client)
    headers = auth_headers(token)
    _create_workflow_with_notification_and_task(client, headers)
    client.post("/api/leads", json={"raw_message": "hi"}, headers=headers)

    response = client.get("/api/tasks", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["title"] == "Follow up"
    assert body["items"][0]["status"] == "open"


def test_update_task_status(client):
    token = register_and_get_token(client)
    headers = auth_headers(token)
    _create_workflow_with_notification_and_task(client, headers)
    client.post("/api/leads", json={"raw_message": "hi"}, headers=headers)

    task_id = client.get("/api/tasks", headers=headers).json()["items"][0]["id"]
    response = client.patch(f"/api/tasks/{task_id}", json={"status": "done"}, headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "done"

    open_tasks = client.get("/api/tasks?status=open", headers=headers).json()
    assert open_tasks["total"] == 0


def test_task_from_other_business_is_404(client):
    token_a = register_and_get_token(client, email="ownera@techfixsolutions.io", business_name="Biz A")
    token_b = register_and_get_token(client, email="ownerb@techfixsolutions.io", business_name="Biz B")
    _create_workflow_with_notification_and_task(client, auth_headers(token_a))
    client.post("/api/leads", json={"raw_message": "hi"}, headers=auth_headers(token_a))

    task_id = client.get("/api/tasks", headers=auth_headers(token_a)).json()["items"][0]["id"]
    response = client.patch(f"/api/tasks/{task_id}", json={"status": "done"}, headers=auth_headers(token_b))
    assert response.status_code == 404


# ---- dashboard summary ----------------------------------------------------------


def test_dashboard_summary_counts_and_recents(client):
    token = register_and_get_token(client)
    headers = auth_headers(token)
    _create_workflow_with_notification_and_task(client, headers)

    client.post("/api/leads", json={"raw_message": "Complaint: broken, this is urgent"}, headers=headers)
    client.post("/api/leads", json={"raw_message": "Need info about pricing"}, headers=headers)

    response = client.get("/api/dashboard/summary", headers=headers)
    assert response.status_code == 200
    body = response.json()

    assert body["total_leads"] == 2
    assert body["new_leads"] == 2
    assert body["leads_last_7_days"] == 2
    assert body["unread_notifications"] == 2  # one notification per lead via the workflow
    assert body["open_tasks"] == 2
    assert len(body["recent_leads"]) == 2
    assert len(body["recent_notifications"]) == 2
    assert len(body["recent_tasks"]) == 2


def test_dashboard_summary_empty_business_has_zero_counts(client):
    token = register_and_get_token(client)
    response = client.get("/api/dashboard/summary", headers=auth_headers(token))
    body = response.json()
    assert body["total_leads"] == 0
    assert body["recent_leads"] == []


def test_dashboard_summary_requires_auth(client):
    response = client.get("/api/dashboard/summary")
    assert response.status_code == 401
