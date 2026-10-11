REGISTER_PAYLOAD = {
    "email": "owner@techfixsolutions.io",
    "password": "supersecret123",
    "full_name": "Techfix Owner",
    "business_name": "TechFix Solutions",
}


def test_register_creates_user_and_returns_token(client):
    response = client.post("/api/auth/register", json=REGISTER_PAYLOAD)
    assert response.status_code == 201
    body = response.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


def test_register_duplicate_email_rejected(client):
    client.post("/api/auth/register", json=REGISTER_PAYLOAD)
    response = client.post("/api/auth/register", json=REGISTER_PAYLOAD)
    assert response.status_code == 409


def test_login_with_correct_credentials(client):
    client.post("/api/auth/register", json=REGISTER_PAYLOAD)
    response = client.post(
        "/api/auth/login", json={"email": REGISTER_PAYLOAD["email"], "password": REGISTER_PAYLOAD["password"]}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_login_with_wrong_password_rejected(client):
    client.post("/api/auth/register", json=REGISTER_PAYLOAD)
    response = client.post(
        "/api/auth/login", json={"email": REGISTER_PAYLOAD["email"], "password": "wrong-password"}
    )
    assert response.status_code == 401


def test_login_with_unknown_email_rejected(client):
    response = client.post(
        "/api/auth/login", json={"email": "nobody@doesnotexist.io", "password": "whatever123"}
    )
    assert response.status_code == 401


def test_me_requires_valid_token(client):
    response = client.get("/api/auth/me")
    assert response.status_code == 401  # no Authorization header

    response = client.get("/api/auth/me", headers={"Authorization": "Bearer garbage.token.value"})
    assert response.status_code == 401


def test_me_returns_current_user_with_valid_token(client):
    register_response = client.post("/api/auth/register", json=REGISTER_PAYLOAD)
    token = register_response.json()["access_token"]

    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == REGISTER_PAYLOAD["email"]
    assert body["role"] == "owner"
    assert body["business_id"] is not None
