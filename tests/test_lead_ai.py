from conftest import auth_headers, register_and_get_token

from app.models.ai_log import AILog


def test_lead_with_message_gets_classified_on_creation(client):
    token = register_and_get_token(client)
    response = client.post(
        "/api/leads",
        json={"raw_message": "I urgently need a quote for catering a corporate lunch, budget $3000"},
        headers=auth_headers(token),
    )
    assert response.status_code == 201
    body = response.json()

    assert body["intent"] == "quote_request"
    assert body["category"] == "catering"
    assert body["confidence"] > 0
    assert body["score"] is not None
    assert 0 <= body["score"] <= 100
    assert body["extracted_data"]["urgency"] == "high"
    assert body["extracted_data"]["budget"] is not None


def test_lead_without_message_has_null_ai_fields(client):
    token = register_and_get_token(client)
    response = client.post("/api/leads", json={}, headers=auth_headers(token))
    assert response.status_code == 201
    body = response.json()

    assert body["intent"] is None
    assert body["score"] is None
    assert body["extracted_data"] is None


def test_lead_auto_creates_customer_from_extracted_email(client):
    token = register_and_get_token(client)
    response = client.post(
        "/api/leads",
        json={"raw_message": "Please contact me at jane@customerdomain.io about a mobile app"},
        headers=auth_headers(token),
    )
    assert response.status_code == 201
    body = response.json()

    assert body["customer_id"] is not None
    assert body["customer"]["email"] == "jane@customerdomain.io"


def test_explicit_customer_payload_takes_priority_over_extraction(client):
    token = register_and_get_token(client)
    response = client.post(
        "/api/leads",
        json={
            "raw_message": "contact me at other@customerdomain.io",
            "customer": {"email": "explicit@customerdomain.io", "name": "Explicit Name"},
        },
        headers=auth_headers(token),
    )
    body = response.json()
    assert body["customer"]["email"] == "explicit@customerdomain.io"


def test_reclassify_endpoint_updates_existing_lead(client):
    token = register_and_get_token(client)
    headers = auth_headers(token)

    create_response = client.post("/api/leads", json={"raw_message": "hi"}, headers=headers)
    lead_id = create_response.json()["id"]
    assert create_response.json()["intent"] is not None  # already classified on create

    # simulate the message being edited after creation, then re-classified
    client.patch(f"/api/leads/{lead_id}", json={"raw_message": "I need a quote urgently, budget $10000"}, headers=headers)

    reclassify_response = client.post(f"/api/leads/{lead_id}/classify", headers=headers)
    assert reclassify_response.status_code == 200
    body = reclassify_response.json()
    assert body["intent"] == "quote_request"
    assert body["extracted_data"]["urgency"] == "high"


def test_reclassify_requires_a_message(client):
    token = register_and_get_token(client)
    headers = auth_headers(token)
    lead_id = client.post("/api/leads", json={}, headers=headers).json()["id"]

    response = client.post(f"/api/leads/{lead_id}/classify", headers=headers)
    assert response.status_code == 400


def test_reclassify_requires_auth_and_ownership(client):
    token_a = register_and_get_token(client, email="ownera@techfixsolutions.io", business_name="Biz A")
    token_b = register_and_get_token(client, email="ownerb@techfixsolutions.io", business_name="Biz B")

    lead_id = client.post(
        "/api/leads", json={"raw_message": "private lead"}, headers=auth_headers(token_a)
    ).json()["id"]

    response = client.post(f"/api/leads/{lead_id}/classify", headers=auth_headers(token_b))
    assert response.status_code == 404


def test_ai_logs_are_attributed_to_the_lead(client):
    token = register_and_get_token(client)
    lead = client.post(
        "/api/leads", json={"raw_message": "Need a quote"}, headers=auth_headers(token)
    ).json()

    session = client.test_session_factory()
    try:
        logs = session.query(AILog).filter(AILog.lead_id == lead["id"]).all()
    finally:
        session.close()

    operations = {log.operation for log in logs}
    assert {"classify", "extract", "score"}.issubset(operations)
