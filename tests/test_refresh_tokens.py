from conftest import auth_headers

REGISTER_PAYLOAD = {
    "email": "owner@techfixsolutions.io",
    "password": "supersecret123",
    "full_name": "Techfix Owner",
    "business_name": "TechFix Solutions",
}


def test_register_returns_both_tokens(client):
    response = client.post("/api/auth/register", json=REGISTER_PAYLOAD)
    body = response.json()
    assert "access_token" in body
    assert "refresh_token" in body
    assert body["token_type"] == "bearer"


def test_login_returns_both_tokens(client):
    client.post("/api/auth/register", json=REGISTER_PAYLOAD)
    response = client.post(
        "/api/auth/login", json={"email": REGISTER_PAYLOAD["email"], "password": REGISTER_PAYLOAD["password"]}
    )
    body = response.json()
    assert "access_token" in body
    assert "refresh_token" in body


def test_refresh_issues_a_new_access_token(client):
    tokens = client.post("/api/auth/register", json=REGISTER_PAYLOAD).json()

    response = client.post("/api/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert response.status_code == 200
    new_access_token = response.json()["access_token"]
    assert new_access_token

    me = client.get("/api/auth/me", headers=auth_headers(new_access_token))
    assert me.status_code == 200
    assert me.json()["email"] == REGISTER_PAYLOAD["email"]


def test_refresh_rejects_token_for_deactivated_user(client):
    owner_tokens = client.post("/api/auth/register", json=REGISTER_PAYLOAD).json()
    staff_tokens = client.post(
        "/api/business/staff",
        json={"email": "staff@techfixsolutions.io", "password": "staffpass123", "full_name": "Staff"},
        headers=auth_headers(owner_tokens["access_token"]),
    )
    staff_login = client.post(
        "/api/auth/login", json={"email": "staff@techfixsolutions.io", "password": "staffpass123"}
    ).json()

    staff_id = next(
        s["id"]
        for s in client.get("/api/business/staff", headers=auth_headers(owner_tokens["access_token"])).json()
        if s["role"] == "staff"
    )
    client.patch(
        f"/api/business/staff/{staff_id}", json={"is_active": False}, headers=auth_headers(owner_tokens["access_token"])
    )

    response = client.post("/api/auth/refresh", json={"refresh_token": staff_login["refresh_token"]})
    assert response.status_code == 401


def test_refresh_rejects_garbage_token(client):
    response = client.post("/api/auth/refresh", json={"refresh_token": "not-a-real-token"})
    assert response.status_code == 401


def test_logout_revokes_the_refresh_token(client):
    tokens = client.post("/api/auth/register", json=REGISTER_PAYLOAD).json()

    logout_response = client.post("/api/auth/logout", json={"refresh_token": tokens["refresh_token"]})
    assert logout_response.status_code == 204

    refresh_response = client.post("/api/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert refresh_response.status_code == 401


def test_logout_does_not_invalidate_the_current_access_token(client):
    """By design: the access token is short-lived and stateless, so it stays
    valid until its own expiry even after logout — that's *why* it's short
    now, not a bug. Logout's job is stopping new access tokens from being minted."""
    tokens = client.post("/api/auth/register", json=REGISTER_PAYLOAD).json()
    client.post("/api/auth/logout", json={"refresh_token": tokens["refresh_token"]})

    me = client.get("/api/auth/me", headers=auth_headers(tokens["access_token"]))
    assert me.status_code == 200


def test_logout_with_unknown_token_is_a_no_op_not_an_error(client):
    response = client.post("/api/auth/logout", json={"refresh_token": "never-issued"})
    assert response.status_code == 204


def test_register_rate_limited_after_five_attempts(client):
    for i in range(5):
        response = client.post(
            "/api/auth/register",
            json={**REGISTER_PAYLOAD, "email": f"owner{i}@techfixsolutions.io"},
        )
        assert response.status_code == 201

    sixth = client.post(
        "/api/auth/register", json={**REGISTER_PAYLOAD, "email": "owner-sixth@techfixsolutions.io"}
    )
    assert sixth.status_code == 429


def test_login_rate_limited_after_ten_attempts(client):
    client.post("/api/auth/register", json=REGISTER_PAYLOAD)

    for _ in range(10):
        response = client.post(
            "/api/auth/login", json={"email": REGISTER_PAYLOAD["email"], "password": "wrong-password"}
        )
        assert response.status_code == 401

    eleventh = client.post(
        "/api/auth/login", json={"email": REGISTER_PAYLOAD["email"], "password": "wrong-password"}
    )
    assert eleventh.status_code == 429
