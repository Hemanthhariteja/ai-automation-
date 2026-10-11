from conftest import auth_headers, register_and_get_token


def test_create_lead_with_customer_info(client):
    token = register_and_get_token(client)
    response = client.post(
        "/api/leads",
        json={
            "raw_message": "Need a website redesign quote",
            "source": "web_form",
            "customer": {"name": "Jane Doe", "email": "jane@customerdomain.io", "phone": "555-1234"},
        },
        headers=auth_headers(token),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "new"
    assert body["priority"] == "normal"
    assert body["customer"]["email"] == "jane@customerdomain.io"


def test_create_lead_without_customer_info(client):
    token = register_and_get_token(client)
    response = client.post(
        "/api/leads", json={"raw_message": "Anonymous enquiry"}, headers=auth_headers(token)
    )
    assert response.status_code == 201
    body = response.json()
    assert body["customer_id"] is None
    assert body["customer"] is None


def test_create_lead_requires_auth(client):
    response = client.post("/api/leads", json={"raw_message": "Hi"})
    assert response.status_code == 401


def test_repeat_customer_email_reuses_customer(client):
    token = register_and_get_token(client)
    headers = auth_headers(token)
    first = client.post(
        "/api/leads",
        json={"raw_message": "first enquiry", "customer": {"email": "jane@customerdomain.io", "name": "Jane"}},
        headers=headers,
    ).json()
    second = client.post(
        "/api/leads",
        json={"raw_message": "second enquiry", "customer": {"email": "jane@customerdomain.io"}},
        headers=headers,
    ).json()
    assert first["customer_id"] == second["customer_id"]


def test_list_leads_scoped_to_own_business(client):
    token_a = register_and_get_token(client, email="ownera@techfixsolutions.io", business_name="Biz A")
    token_b = register_and_get_token(client, email="ownerb@techfixsolutions.io", business_name="Biz B")

    client.post("/api/leads", json={"raw_message": "lead for A"}, headers=auth_headers(token_a))
    client.post("/api/leads", json={"raw_message": "lead for B 1"}, headers=auth_headers(token_b))
    client.post("/api/leads", json={"raw_message": "lead for B 2"}, headers=auth_headers(token_b))

    response_a = client.get("/api/leads", headers=auth_headers(token_a))
    response_b = client.get("/api/leads", headers=auth_headers(token_b))

    assert response_a.json()["total"] == 1
    assert response_b.json()["total"] == 2


def test_get_lead_from_other_business_is_404(client):
    token_a = register_and_get_token(client, email="ownera@techfixsolutions.io", business_name="Biz A")
    token_b = register_and_get_token(client, email="ownerb@techfixsolutions.io", business_name="Biz B")

    lead = client.post(
        "/api/leads", json={"raw_message": "private to A"}, headers=auth_headers(token_a)
    ).json()

    response = client.get(f"/api/leads/{lead['id']}", headers=auth_headers(token_b))
    assert response.status_code == 404


def test_get_nonexistent_lead_is_404(client):
    token = register_and_get_token(client)
    response = client.get("/api/leads/9999", headers=auth_headers(token))
    assert response.status_code == 404


def test_update_lead_status_and_priority(client):
    token = register_and_get_token(client)
    headers = auth_headers(token)
    lead = client.post("/api/leads", json={"raw_message": "update me"}, headers=headers).json()

    response = client.patch(
        f"/api/leads/{lead['id']}", json={"status": "qualified", "priority": "high"}, headers=headers
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "qualified"
    assert body["priority"] == "high"


def test_update_lead_rejects_invalid_status(client):
    token = register_and_get_token(client)
    headers = auth_headers(token)
    lead = client.post("/api/leads", json={"raw_message": "bad update"}, headers=headers).json()

    response = client.patch(f"/api/leads/{lead['id']}", json={"status": "not_a_real_status"}, headers=headers)
    assert response.status_code == 422


def test_delete_lead(client):
    token = register_and_get_token(client)
    headers = auth_headers(token)
    lead = client.post("/api/leads", json={"raw_message": "delete me"}, headers=headers).json()

    delete_response = client.delete(f"/api/leads/{lead['id']}", headers=headers)
    assert delete_response.status_code == 204

    get_response = client.get(f"/api/leads/{lead['id']}", headers=headers)
    assert get_response.status_code == 404


def test_filter_leads_by_status(client):
    token = register_and_get_token(client)
    headers = auth_headers(token)
    lead1 = client.post("/api/leads", json={"raw_message": "one"}, headers=headers).json()
    client.post("/api/leads", json={"raw_message": "two"}, headers=headers)
    client.patch(f"/api/leads/{lead1['id']}", json={"status": "won"}, headers=headers)

    response = client.get("/api/leads?status=won", headers=headers)
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == lead1["id"]


def test_search_leads_by_message_content(client):
    token = register_and_get_token(client)
    headers = auth_headers(token)
    client.post("/api/leads", json={"raw_message": "need a mobile app quote"}, headers=headers)
    client.post("/api/leads", json={"raw_message": "digital marketing question"}, headers=headers)

    response = client.get("/api/leads?search=mobile", headers=headers)
    body = response.json()
    assert body["total"] == 1
    assert "mobile" in body["items"][0]["raw_message"]
