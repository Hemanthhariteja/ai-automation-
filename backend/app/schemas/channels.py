from typing import Optional

from pydantic import BaseModel, Field


class SimulateMessengerMessage(BaseModel):
    sender_id: str = Field(min_length=1, max_length=200)
    text: str = Field(min_length=1, max_length=4000)
    sender_name: Optional[str] = Field(default=None, max_length=200)


class ChannelStatus(BaseModel):
    name: str
    configured: bool
    message: str
    business_connected: bool


class ChannelsStatusResponse(BaseModel):
    channels: list[ChannelStatus]
