from conftest import auth_headers, register_and_get_token


def test_get_profile_starts_with_only_name_set(client):
    token = register_and_get_token(client)
    response = client.get("/api/business/profile", headers=auth_headers(token))
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "TechFix Solutions"
    assert body["description"] is None
    assert body["tone"] == "professional"


def test_update_profile_persists_fields(client):
    token = register_and_get_token(client)
    headers = auth_headers(token)

    response = client.patch(
        "/api/business/profile",
        json={
            "description": "We build websites, apps, and AI automation for small businesses.",
            "services": "Website development, digital marketing, mobile apps, AI automation",
            "hours": "Mon-Fri 9am-6pm",
            "contact_email": "hello@techfixsolutions.io",
            "contact_phone": "555-0100",
            "tone": "friendly",
        },
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["services"] == "Website development, digital marketing, mobile apps, AI automation"
    assert body["tone"] == "friendly"

    refetched = client.get("/api/business/profile", headers=headers).json()
    assert refetched["contact_email"] == "hello@techfixsolutions.io"


def test_profile_requires_auth(client):
    response = client.get("/api/business/profile")
    assert response.status_code == 401
