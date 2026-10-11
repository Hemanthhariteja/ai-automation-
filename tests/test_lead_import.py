import io

from conftest import auth_headers, register_and_get_token


def _upload(client, headers, csv_text):
    return client.post(
        "/api/leads/import",
        files={"file": ("leads.csv", io.BytesIO(csv_text.encode("utf-8")), "text/csv")},
        headers=headers,
    )


def test_import_template_downloadable(client):
    response = client.get("/api/leads/import/template")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "message" in response.text


def test_import_creates_classified_leads(client):
    token = register_and_get_token(client)
    headers = auth_headers(token)
    csv_text = (
        "message,name,email\n"
        '"I need a quote for a website, budget $2000, urgent",Jane Doe,jane@customerdomain.io\n'
        '"Complaint: app is broken and not working",Raj Mehta,raj@customerdomain.io\n'
    )

    response = _upload(client, headers, csv_text)
    assert response.status_code == 200
    body = response.json()
    assert body["total_rows"] == 2
    assert body["imported"] == 2
    assert body["skipped"] == 0
    assert body["errors"] == []

    leads = client.get("/api/leads", headers=headers).json()
    assert leads["total"] == 2
    assert all(lead["source"] == "import" for lead in leads["items"])
    assert any(lead["intent"] == "complaint" for lead in leads["items"])


def test_import_skips_rows_missing_message(client):
    token = register_and_get_token(client)
    headers = auth_headers(token)
    csv_text = "message,name\n" '"valid message here",Jane\n' ',No Message Person\n'

    response = _upload(client, headers, csv_text)
    body = response.json()
    assert body["total_rows"] == 2
    assert body["imported"] == 1
    assert body["skipped"] == 1
    assert body["errors"][0]["row"] == 2
    assert "Missing message" in body["errors"][0]["reason"]


def test_import_accepts_raw_message_header_alias(client):
    token = register_and_get_token(client)
    headers = auth_headers(token)
    csv_text = 'raw_message,customer_email\n"Need info about pricing",x@customerdomain.io\n'

    response = _upload(client, headers, csv_text)
    assert response.json()["imported"] == 1


def test_import_rejects_csv_without_message_column(client):
    token = register_and_get_token(client)
    headers = auth_headers(token)
    csv_text = "name,email\nJane,jane@customerdomain.io\n"

    response = _upload(client, headers, csv_text)
    assert response.status_code == 400


def test_import_rejects_too_many_rows(client):
    token = register_and_get_token(client)
    headers = auth_headers(token)
    rows = "\n".join(f'"enquiry number {i}"' for i in range(501))
    csv_text = f"message\n{rows}\n"

    response = _upload(client, headers, csv_text)
    assert response.status_code == 400
    assert "500" in response.json()["detail"]


def test_import_triggers_workflows(client):
    token = register_and_get_token(client)
    headers = auth_headers(token)
    client.post("/api/workflows/templates/complaint_priority", headers=headers)

    csv_text = 'message\n"Complaint: broken and not working"\n'
    _upload(client, headers, csv_text)

    leads = client.get("/api/leads", headers=headers).json()
    assert leads["items"][0]["priority"] == "high"


def test_import_requires_auth(client):
    response = client.post(
        "/api/leads/import", files={"file": ("leads.csv", io.BytesIO(b"message\nhi\n"), "text/csv")}
    )
    assert response.status_code == 401


def test_import_isolated_per_business(client):
    token_a = register_and_get_token(client, email="ownera@techfixsolutions.io", business_name="Biz A")
    token_b = register_and_get_token(client, email="ownerb@techfixsolutions.io", business_name="Biz B")

    _upload(client, auth_headers(token_a), 'message\n"hello from A"\n')

    leads_b = client.get("/api/leads", headers=auth_headers(token_b)).json()
    assert leads_b["total"] == 0
