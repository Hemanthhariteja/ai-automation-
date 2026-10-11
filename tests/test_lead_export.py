import csv
import io

from conftest import auth_headers, register_and_get_token


def _create_lead(client, headers, message, name=None, email=None):
    customer = {"name": name, "email": email} if (name or email) else None
    payload = {"raw_message": message}
    if customer:
        payload["customer"] = customer
    return client.post("/api/leads", json=payload, headers=headers)


def test_export_leads_csv_includes_created_leads(client):
    token = register_and_get_token(client)
    headers = auth_headers(token)
    _create_lead(client, headers, "I need a quote for catering, budget $2000", "Jane Doe", "jane@example.io")
    _create_lead(client, headers, "Complaint: food arrived cold")

    response = client.get("/api/leads/export", headers=headers)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "attachment" in response.headers["content-disposition"]

    rows = list(csv.DictReader(io.StringIO(response.text)))
    assert len(rows) == 2
    assert {"id", "status", "priority", "intent", "score", "raw_message"}.issubset(rows[0].keys())
    messages = {row["raw_message"] for row in rows}
    assert "I need a quote for catering, budget $2000" in messages
    jane_row = next(row for row in rows if row["customer_name"] == "Jane Doe")
    assert jane_row["customer_email"] == "jane@example.io"


def test_export_leads_csv_respects_filters(client):
    token = register_and_get_token(client)
    headers = auth_headers(token)
    _create_lead(client, headers, "I need a quote for catering, budget $2000")
    _create_lead(client, headers, "Complaint: food arrived cold")

    response = client.get("/api/leads/export", params={"search": "catering"}, headers=headers)
    rows = list(csv.DictReader(io.StringIO(response.text)))
    assert len(rows) == 1
    assert "catering" in rows[0]["raw_message"]


def test_export_leads_requires_auth(client):
    response = client.get("/api/leads/export")
    assert response.status_code == 401


def test_export_leads_only_includes_own_business(client):
    token_a = register_and_get_token(client, email="ownera@example.io", business_name="Biz A")
    _create_lead(client, auth_headers(token_a), "Table for 4 this Friday")

    token_b = register_and_get_token(client, email="ownerb@example.io", business_name="Biz B")
    headers_b = auth_headers(token_b)
    _create_lead(client, headers_b, "Catering for a corporate lunch")

    response = client.get("/api/leads/export", headers=headers_b)
    rows = list(csv.DictReader(io.StringIO(response.text)))
    assert len(rows) == 1
    assert "Catering" in rows[0]["raw_message"]


def test_export_customers_csv(client):
    token = register_and_get_token(client)
    headers = auth_headers(token)
    _create_lead(client, headers, "Table for 4", "Jane Doe", "jane@example.io")

    response = client.get("/api/leads/export/customers", headers=headers)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")

    rows = list(csv.DictReader(io.StringIO(response.text)))
    assert len(rows) == 1
    assert rows[0]["name"] == "Jane Doe"
    assert rows[0]["email"] == "jane@example.io"
    assert rows[0]["lead_count"] == "1"


def test_export_customers_requires_auth(client):
    response = client.get("/api/leads/export/customers")
    assert response.status_code == 401
