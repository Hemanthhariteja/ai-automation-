from conftest import auth_headers, register_and_get_token


def _create_lead_with_message(client, headers, message="I need a quote for a website"):
    return client.post("/api/leads", json={"raw_message": message}, headers=headers).json()


def test_generate_response_requires_a_message(client):
    token = register_and_get_token(client)
    headers = auth_headers(token)
    lead = client.post("/api/leads", json={}, headers=headers).json()

    response = client.post(f"/api/leads/{lead['id']}/generate-response", headers=headers)
    assert response.status_code == 400


def test_generate_response_creates_conversation_with_both_messages(client):
    token = register_and_get_token(client)
    headers = auth_headers(token)
    lead = _create_lead_with_message(client, headers)

    response = client.post(f"/api/leads/{lead['id']}/generate-response", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["message"]["sender"] == "ai"
    assert body["message"]["content"]
    assert body["provider_used"] == "demo"
    assert body["fallback_used"] is False

    conversation = client.get(f"/api/leads/{lead['id']}/conversation", headers=headers).json()
    senders = [m["sender"] for m in conversation["messages"]]
    assert senders == ["customer", "ai"]


def test_generated_response_is_grounded_in_configured_profile(client):
    token = register_and_get_token(client)
    headers = auth_headers(token)

    client.patch(
        "/api/business/profile",
        json={"services": "Website development and AI automation", "hours": "Mon-Fri 9am-6pm"},
        headers=headers,
    )
    lead = _create_lead_with_message(client, headers)

    response = client.post(f"/api/leads/{lead['id']}/generate-response", headers=headers)
    text = response.json()["message"]["content"]
    assert "Website development and AI automation" in text
    assert "Mon-Fri 9am-6pm" in text
    assert "TechFix Solutions" in text


def test_generated_response_never_invents_unconfigured_fields(client):
    token = register_and_get_token(client)
    headers = auth_headers(token)
    # deliberately leave services/hours/contact unset
    lead = _create_lead_with_message(client, headers)

    response = client.post(f"/api/leads/{lead['id']}/generate-response", headers=headers)
    text = response.json()["message"]["content"]
    # no price, policy, or promise text should appear when nothing was configured
    assert "$" not in text
    assert "free" not in text.lower()
    assert "guarantee" not in text.lower()


def test_generate_response_requires_auth_and_ownership(client):
    token_a = register_and_get_token(client, email="ownera@techfixsolutions.io", business_name="Biz A")
    token_b = register_and_get_token(client, email="ownerb@techfixsolutions.io", business_name="Biz B")

    lead = _create_lead_with_message(client, auth_headers(token_a))

    response = client.post(f"/api/leads/{lead['id']}/generate-response", headers=auth_headers(token_b))
    assert response.status_code == 404

    response = client.post(f"/api/leads/{lead['id']}/generate-response")
    assert response.status_code == 401


def test_summarize_conversation(client):
    token = register_and_get_token(client)
    headers = auth_headers(token)
    lead = _create_lead_with_message(
        client, headers, message="I need a quote for a website, budget $2000, fairly urgent"
    )
    client.post(f"/api/leads/{lead['id']}/generate-response", headers=headers)

    response = client.post(f"/api/leads/{lead['id']}/summarize", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["summary"]
    assert body["provider_used"] == "demo"

    conversation = client.get(f"/api/leads/{lead['id']}/conversation", headers=headers).json()
    assert conversation["summary"] == body["summary"]


def test_conversation_endpoint_creates_conversation_even_before_any_response(client):
    token = register_and_get_token(client)
    headers = auth_headers(token)
    lead = _create_lead_with_message(client, headers)

    response = client.get(f"/api/leads/{lead['id']}/conversation", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert len(body["messages"]) == 1
    assert body["messages"][0]["sender"] == "customer"
