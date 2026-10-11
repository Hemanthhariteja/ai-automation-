import hashlib
import hmac
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

import pytest
from conftest import auth_headers, register_and_get_token

from app.channels.base import ChannelError
from app.channels.messenger import MessengerChannel
from app.channels.mock import MockChannel

MESSENGER_PAYLOAD = {
    "object": "page",
    "entry": [
        {
            "id": "1234567890",
            "messaging": [
                {"sender": {"id": "psid-abc"}, "recipient": {"id": "1234567890"}, "message": {"text": "Table for 4 tonight?"}}
            ],
        }
    ],
}


# ---- unit tests: channel parsers -------------------------------------------


def test_messenger_channel_parses_a_text_message():
    messages = MessengerChannel().parse_webhook_payload(MESSENGER_PAYLOAD)
    assert len(messages) == 1
    assert messages[0].sender_external_id == "psid-abc"
    assert messages[0].text == "Table for 4 tonight?"


def test_messenger_channel_skips_non_text_events():
    payload = {
        "object": "page",
        "entry": [{"id": "123", "messaging": [{"sender": {"id": "psid-1"}, "delivery": {"mids": ["m1"]}}]}],
    }
    assert MessengerChannel().parse_webhook_payload(payload) == []


def test_messenger_channel_rejects_malformed_payload():
    with pytest.raises(ChannelError):
        MessengerChannel().parse_webhook_payload({"not_entry": True})


def test_messenger_channel_extracts_page_id():
    assert MessengerChannel.page_id_from_payload(MESSENGER_PAYLOAD) == "1234567890"
    assert MessengerChannel.page_id_from_payload({"entry": []}) is None


def test_messenger_signature_verification():
    body = b'{"hello":"world"}'
    secret = "test-secret"
    valid_sig = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

    assert MessengerChannel.verify_signature(body, valid_sig, secret) is True
    assert MessengerChannel.verify_signature(body, "sha256=wrong", secret) is False
    assert MessengerChannel.verify_signature(body, None, secret) is False
    # No app secret configured — skipped entirely (the zero-setup local path)
    assert MessengerChannel.verify_signature(body, None, "") is True


def test_mock_channel_parses_a_message():
    messages = MockChannel().parse_webhook_payload({"sender_id": "u1", "sender_name": "Jane", "text": "hi"})
    assert messages[0].sender_external_id == "u1"
    assert messages[0].sender_name == "Jane"


def test_mock_channel_requires_sender_and_text():
    with pytest.raises(ChannelError):
        MockChannel().parse_webhook_payload({"sender_id": "u1"})


# ---- API: status ------------------------------------------------------------


def test_channels_status_unconfigured_by_default(client):
    token = register_and_get_token(client)
    response = client.get("/api/channels/status", headers=auth_headers(token))
    assert response.status_code == 200
    body = response.json()
    messenger = next(c for c in body["channels"] if c["name"] == "messenger")
    mock = next(c for c in body["channels"] if c["name"] == "mock")
    assert messenger["configured"] is False
    assert messenger["business_connected"] is False
    assert mock["configured"] is True  # always available, zero setup


def test_channels_status_requires_auth(client):
    response = client.get("/api/channels/status")
    assert response.status_code == 401


def test_business_connected_after_setting_page_id(client):
    token = register_and_get_token(client)
    headers = auth_headers(token)
    client.patch("/api/business/profile", json={"messenger_page_id": "page-123"}, headers=headers)

    status = client.get("/api/channels/status", headers=headers).json()
    messenger = next(c for c in status["channels"] if c["name"] == "messenger")
    assert messenger["business_connected"] is True


# ---- API: simulate (zero-setup demo path) -----------------------------------


def test_simulate_creates_a_classified_lead(client):
    token = register_and_get_token(client)
    headers = auth_headers(token)

    response = client.post(
        "/api/channels/messenger/simulate",
        json={"sender_id": "psid-1", "sender_name": "Jane", "text": "Can I book a table for 4 this Saturday?"},
        headers=headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["source"] == "messenger"
    assert body["intent"] is not None  # AI pipeline ran
    assert body["tracking_data"]["sender_external_id"] == "psid-1"
    assert body["customer"]["name"] == "Jane"


def test_simulate_triggers_workflows(client):
    token = register_and_get_token(client)
    headers = auth_headers(token)
    client.post("/api/workflows/templates/complaint_priority", headers=headers)

    response = client.post(
        "/api/channels/messenger/simulate",
        json={"sender_id": "psid-2", "text": "Complaint: the food was cold and service was slow"},
        headers=headers,
    )
    assert response.json()["priority"] == "high"


def test_simulate_requires_auth(client):
    response = client.post("/api/channels/messenger/simulate", json={"sender_id": "u1", "text": "hi"})
    assert response.status_code == 401


def test_simulate_isolated_per_business(client):
    token_a = register_and_get_token(client, email="ownera@example.io", business_name="Biz A")
    token_b = register_and_get_token(client, email="ownerb@example.io", business_name="Biz B")

    client.post(
        "/api/channels/messenger/simulate",
        json={"sender_id": "u1", "text": "hi"},
        headers=auth_headers(token_a),
    )
    leads_b = client.get("/api/leads", headers=auth_headers(token_b)).json()
    assert leads_b["total"] == 0


# ---- API: real webhook -------------------------------------------------------


def test_webhook_verification_handshake_succeeds(client, monkeypatch):
    from app.api import channels as channels_module

    monkeypatch.setattr(channels_module.settings, "facebook_verify_token", "my-verify-token")
    response = client.get(
        "/api/channels/messenger/webhook",
        params={"hub.mode": "subscribe", "hub.verify_token": "my-verify-token", "hub.challenge": "12345"},
    )
    assert response.status_code == 200
    assert response.text == "12345"


def test_webhook_verification_handshake_rejects_wrong_token(client, monkeypatch):
    from app.api import channels as channels_module

    monkeypatch.setattr(channels_module.settings, "facebook_verify_token", "my-verify-token")
    response = client.get(
        "/api/channels/messenger/webhook",
        params={"hub.mode": "subscribe", "hub.verify_token": "wrong", "hub.challenge": "12345"},
    )
    assert response.status_code == 403


def test_real_webhook_ignored_when_no_business_connected(client):
    response = client.post("/api/channels/messenger/webhook", json=MESSENGER_PAYLOAD)
    assert response.status_code == 200
    assert response.json()["status"] == "ignored"


def test_real_webhook_creates_lead_for_connected_business(client):
    token = register_and_get_token(client)
    headers = auth_headers(token)
    client.patch("/api/business/profile", json={"messenger_page_id": "1234567890"}, headers=headers)

    response = client.post("/api/channels/messenger/webhook", json=MESSENGER_PAYLOAD)
    assert response.status_code == 200
    assert response.json()["leads_created"] == 1

    leads = client.get("/api/leads", headers=headers).json()
    assert leads["total"] == 1
    assert leads["items"][0]["source"] == "messenger"
    assert leads["items"][0]["raw_message"] == "Table for 4 tonight?"


def test_real_webhook_rejects_bad_signature_when_app_secret_configured(client, monkeypatch):
    from app.api import channels as channels_module

    monkeypatch.setattr(channels_module.settings, "facebook_app_secret", "shh")
    response = client.post(
        "/api/channels/messenger/webhook",
        content=json.dumps(MESSENGER_PAYLOAD),
        headers={"Content-Type": "application/json", "X-Hub-Signature-256": "sha256=wrong"},
    )
    assert response.status_code == 403


def test_real_webhook_accepts_valid_signature(client, monkeypatch):
    from app.api import channels as channels_module

    monkeypatch.setattr(channels_module.settings, "facebook_app_secret", "shh")
    token = register_and_get_token(client)
    client.patch(
        "/api/business/profile", json={"messenger_page_id": "1234567890"}, headers=auth_headers(token)
    )

    body = json.dumps(MESSENGER_PAYLOAD).encode()
    sig = "sha256=" + hmac.new(b"shh", body, hashlib.sha256).hexdigest()
    response = client.post(
        "/api/channels/messenger/webhook",
        content=body,
        headers={"Content-Type": "application/json", "X-Hub-Signature-256": sig},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_real_webhook_malformed_json_does_not_crash(client):
    response = client.post(
        "/api/channels/messenger/webhook", content=b"not json", headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "ignored"
