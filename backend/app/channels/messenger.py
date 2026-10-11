import hashlib
import hmac

from app.channels.base import Channel, ChannelError, InboundMessage


class MessengerChannel(Channel):
    """Parses Meta's Messenger/Instagram webhook payload shape:
    {"object": "page", "entry": [{"id": "<page_id>",
     "messaging": [{"sender": {"id": "<psid>"}, "message": {"text": "..."}}]}]}
    Non-text events (read receipts, postbacks, reactions) are skipped, not
    errors — a real Page sends plenty of those and only text messages become leads."""

    name = "messenger"

    def parse_webhook_payload(self, payload: dict) -> list[InboundMessage]:
        if not isinstance(payload, dict) or "entry" not in payload:
            raise ChannelError("Payload is missing the expected 'entry' field")

        messages: list[InboundMessage] = []
        for entry in payload.get("entry", []):
            for event in entry.get("messaging", []):
                text = event.get("message", {}).get("text")
                sender_id = event.get("sender", {}).get("id")
                if not text or not sender_id:
                    continue  # a read receipt, postback, etc. — not a message
                messages.append(InboundMessage(sender_external_id=sender_id, text=text))
        return messages

    @staticmethod
    def page_id_from_payload(payload: dict) -> str | None:
        entries = payload.get("entry", [])
        return entries[0].get("id") if entries else None

    @staticmethod
    def verify_signature(raw_body: bytes, signature_header: str | None, app_secret: str) -> bool:
        """Meta signs each webhook delivery with the app secret; verifying
        it stops anyone who finds the webhook URL from injecting fake leads.
        Skipped entirely (returns True) if no app secret is configured —
        there's no real Meta app to receive from locally, so demanding a
        signature would just break the zero-setup path this whole channel
        is built around."""
        if not app_secret:
            return True
        if not signature_header or not signature_header.startswith("sha256="):
            return False
        expected = hmac.new(app_secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
        provided = signature_header.removeprefix("sha256=")
        return hmac.compare_digest(expected, provided)
