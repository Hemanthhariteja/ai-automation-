from app.channels.base import Channel, ChannelError, InboundMessage


class MockChannel(Channel):
    """The zero-setup path — lets Messenger's whole intake flow be tested
    and demoed without a real Meta app, Page, or webhook subscription, the
    same role MockProvider plays for the AI layer. Payload shape:
    {"sender_id": "...", "sender_name": "...", "text": "..."}"""

    name = "mock"

    def parse_webhook_payload(self, payload: dict) -> list[InboundMessage]:
        text = payload.get("text")
        sender_id = payload.get("sender_id")
        if not text or not sender_id:
            raise ChannelError("Simulated message needs at least 'sender_id' and 'text'")
        return [InboundMessage(sender_external_id=sender_id, text=text, sender_name=payload.get("sender_name"))]
