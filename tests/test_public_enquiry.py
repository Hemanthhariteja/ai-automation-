from conftest import auth_headers, register_and_get_token

from app.utils.rate_limit import _hits


def test_registration_generates_a_slug(client):
    token = register_and_get_token(client)
    profile = client.get("/api/business/profile", headers=auth_headers(token)).json()
    assert profile["slug"] == "techfix-solutions"


def test_duplicate_business_names_get_distinct_slugs(client):
    token_a = register_and_get_token(client, email="ownera@techfixsolutions.io", business_name="Acme Co")
    token_b = register_and_get_token(client, email="ownerb@techfixsolutions.io", business_name="Acme Co")

    slug_a = client.get("/api/business/profile", headers=auth_headers(token_a)).json()["slug"]
    slug_b = client.get("/api/business/profile", headers=auth_headers(token_b)).json()["slug"]
    assert slug_a != slug_b
    assert slug_a == "acme-co"
    assert slug_b.startswith("acme-co-")


def test_public_business_info(client):
    token = register_and_get_token(client)
    headers = auth_headers(token)
    client.patch("/api/business/profile", json={"services": "Website development"}, headers=headers)
    slug = client.get("/api/business/profile", headers=headers).json()["slug"]

    response = client.get(f"/api/public/{slug}/business")
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "TechFix Solutions"
    assert body["services"] == "Website development"


def test_public_business_info_404_for_unknown_slug(client):
    response = client.get("/api/public/not-a-real-business/business")
    assert response.status_code == 404


def test_public_enquiry_creates_a_classified_lead_with_no_auth(client):
    token = register_and_get_token(client)
    headers = auth_headers(token)
    slug = client.get("/api/business/profile", headers=headers).json()["slug"]

    response = client.post(
        f"/api/public/{slug}/leads",
        json={"message": "I need a quote for a website, budget $2000, urgent", "name": "Jane", "email": "jane@customerdomain.io"},
    )
    assert response.status_code == 201
    assert response.json() == {"received": True}  # no lead detail leaked publicly

    leads = client.get("/api/leads", headers=headers).json()
    assert leads["total"] == 1
    lead = leads["items"][0]
    assert lead["source"] == "web_form"
    assert lead["intent"] == "quote_request"  # AI pipeline ran
    assert lead["customer"]["email"] == "jane@customerdomain.io"


def test_public_enquiry_404_for_unknown_slug(client):
    response = client.post("/api/public/not-a-real-business/leads", json={"message": "hi"})
    assert response.status_code == 404


def test_public_enquiry_triggers_workflows(client):
    token = register_and_get_token(client)
    headers = auth_headers(token)
    client.post("/api/workflows/templates/complaint_priority", headers=headers)
    slug = client.get("/api/business/profile", headers=headers).json()["slug"]

    client.post(f"/api/public/{slug}/leads", json={"message": "Complaint: this is broken and not working"})

    leads = client.get("/api/leads", headers=headers).json()
    assert leads["items"][0]["priority"] == "high"


def test_public_enquiry_captures_utm_and_click_ids(client):
    token = register_and_get_token(client)
    headers = auth_headers(token)
    slug = client.get("/api/business/profile", headers=headers).json()["slug"]

    client.post(
        f"/api/public/{slug}/leads",
        json={
            "message": "Saw your ad, interested in a website",
            "tracking": {
                "utm_source": "facebook",
                "utm_medium": "cpc",
                "utm_campaign": "summer_sale",
                "fbclid": "abc123",
                "landing_page": f"https://example.io/enquiry/{slug}?utm_source=facebook",
                "referrer": "https://facebook.com/",
            },
        },
    )

    leads = client.get("/api/leads", headers=headers).json()
    tracking = leads["items"][0]["tracking_data"]
    assert tracking["utm_source"] == "facebook"
    assert tracking["utm_campaign"] == "summer_sale"
    assert tracking["fbclid"] == "abc123"
    assert "user_agent" in tracking  # captured server-side regardless of client payload


def test_public_enquiry_without_tracking_still_captures_user_agent(client):
    token = register_and_get_token(client)
    headers = auth_headers(token)
    slug = client.get("/api/business/profile", headers=headers).json()["slug"]

    client.post(f"/api/public/{slug}/leads", json={"message": "no tracking info here"})

    leads = client.get("/api/leads", headers=headers).json()
    tracking = leads["items"][0]["tracking_data"]
    assert tracking is not None
    assert "user_agent" in tracking


def test_public_enquiry_rate_limited_after_five_submissions(client):
    token = register_and_get_token(client)
    slug = client.get("/api/business/profile", headers=auth_headers(token)).json()["slug"]
    _hits.clear()  # isolate from any rate-limit state left by earlier tests in this run

    for _ in range(5):
        response = client.post(f"/api/public/{slug}/leads", json={"message": "hi"})
        assert response.status_code == 201

    sixth = client.post(f"/api/public/{slug}/leads", json={"message": "hi"})
    assert sixth.status_code == 429
