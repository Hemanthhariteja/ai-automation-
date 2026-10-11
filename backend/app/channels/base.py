from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class InboundMessage:
    """A normalized inbound message, regardless of which platform it came
    from — this is what lets the intake pipeline stay channel-agnostic."""

    sender_external_id: str  # platform-specific user id (e.g. Messenger PSID)
    text: str
    sender_name: Optional[str] = None


class ChannelError(Exception):
    """Raised when a webhook payload can't be parsed — caught by the
    endpoint and turned into a clean response, never a 500."""


class Channel(ABC):
    """Common interface every inbound channel implements. Unlike the AI
    provider abstraction, channels aren't mutually-exclusive alternatives
    with a fallback chain — a business can have several active at once (web
    form, public enquiry page, Messenger). What they share is a single
    contract for turning a platform-specific payload into the same
    InboundMessage shape, so the intake pipeline downstream never needs to
    know which channel a message arrived on."""

    name: str

    @abstractmethod
    def parse_webhook_payload(self, payload: dict) -> list[InboundMessage]:
        """Returns zero or more normalized messages found in one webhook
        call (a single Meta webhook delivery can batch multiple events)."""
