from conftest import auth_headers, register_and_get_token


def _create_staff_and_login(client, owner_headers, email="staff@techfixsolutions.io", password="staffpass123"):
    client.post("/api/business/staff", json={"email": email, "password": password, "full_name": "Staff Member"}, headers=owner_headers)
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    return response.json()["access_token"]


def test_owner_can_create_staff_account(client):
    token = register_and_get_token(client)
    headers = auth_headers(token)

    response = client.post(
        "/api/business/staff",
        json={"email": "staff@techfixsolutions.io", "password": "staffpass123", "full_name": "Staff Member"},
        headers=headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["role"] == "staff"
    assert body["is_active"] is True


def test_staff_cannot_create_other_staff(client):
    token = register_and_get_token(client)
    headers = auth_headers(token)
    staff_token = _create_staff_and_login(client, headers)

    response = client.post(
        "/api/business/staff",
        json={"email": "another@techfixsolutions.io", "password": "staffpass123", "full_name": "Another"},
        headers=auth_headers(staff_token),
    )
    assert response.status_code == 403


def test_staff_login_and_me(client):
    token = register_and_get_token(client)
    headers = auth_headers(token)
    staff_token = _create_staff_and_login(client, headers)

    me = client.get("/api/auth/me", headers=auth_headers(staff_token))
    assert me.status_code == 200
    assert me.json()["role"] == "staff"
    assert me.json()["business_id"] == client.get("/api/auth/me", headers=headers).json()["business_id"]


def test_staff_cannot_change_ai_settings(client):
    token = register_and_get_token(client)
    headers = auth_headers(token)
    staff_token = _create_staff_and_login(client, headers)

    response = client.patch("/api/ai/settings", json={"ai_provider": "local"}, headers=auth_headers(staff_token))
    assert response.status_code == 403


def test_owner_can_change_ai_settings(client):
    token = register_and_get_token(client)
    response = client.patch("/api/ai/settings", json={"ai_provider": "local"}, headers=auth_headers(token))
    assert response.status_code == 200


def test_staff_cannot_update_business_profile(client):
    token = register_and_get_token(client)
    headers = auth_headers(token)
    staff_token = _create_staff_and_login(client, headers)

    response = client.patch(
        "/api/business/profile", json={"services": "hacked"}, headers=auth_headers(staff_token)
    )
    assert response.status_code == 403


def test_staff_can_still_do_operational_work(client):
    """Staff aren't locked out of the app — just owner-level settings."""
    token = register_and_get_token(client)
    headers = auth_headers(token)
    staff_token = _create_staff_and_login(client, headers)
    staff_headers = auth_headers(staff_token)

    lead = client.post("/api/leads", json={"raw_message": "hi"}, headers=staff_headers)
    assert lead.status_code == 201

    workflow = client.post("/api/workflows", json={"name": "wf", "trigger_type": "manual"}, headers=staff_headers)
    assert workflow.status_code == 201

    dashboard = client.get("/api/dashboard/summary", headers=staff_headers)
    assert dashboard.status_code == 200


def test_owner_can_deactivate_staff(client):
    token = register_and_get_token(client)
    headers = auth_headers(token)
    client.post(
        "/api/business/staff",
        json={"email": "staff@techfixsolutions.io", "password": "staffpass123", "full_name": "Staff Member"},
        headers=headers,
    )
    staff_list = client.get("/api/business/staff", headers=headers).json()
    staff_id = next(s["id"] for s in staff_list if s["role"] == "staff")

    response = client.patch(f"/api/business/staff/{staff_id}", json={"is_active": False}, headers=headers)
    assert response.status_code == 200
    assert response.json()["is_active"] is False

    login_attempt = client.post(
        "/api/auth/login", json={"email": "staff@techfixsolutions.io", "password": "staffpass123"}
    )
    assert login_attempt.status_code == 403


def test_staff_management_isolated_per_business(client):
    token_a = register_and_get_token(client, email="ownera@techfixsolutions.io", business_name="Biz A")
    token_b = register_and_get_token(client, email="ownerb@techfixsolutions.io", business_name="Biz B")

    client.post(
        "/api/business/staff",
        json={"email": "staff@techfixsolutions.io", "password": "staffpass123", "full_name": "Staff A"},
        headers=auth_headers(token_a),
    )

    staff_b = client.get("/api/business/staff", headers=auth_headers(token_b)).json()
    assert len(staff_b) == 1  # only Owner B themself, not Business A's staff


def test_duplicate_staff_email_rejected(client):
    token = register_and_get_token(client)
    headers = auth_headers(token)
    payload = {"email": "staff@techfixsolutions.io", "password": "staffpass123", "full_name": "Staff Member"}
    client.post("/api/business/staff", json=payload, headers=headers)

    response = client.post("/api/business/staff", json=payload, headers=headers)
    assert response.status_code == 409
