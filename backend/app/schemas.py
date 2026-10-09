from datetime import datetime

from pydantic import BaseModel, Field


class VerifyIn(BaseModel):
    message: str
    signature: str


class JoinIn(BaseModel):
    token_id: int


class SubmitIn(BaseModel):
    token_id: int
    proof_text: str | None = Field(default=None, max_length=2000)
    proof_url: str | None = Field(default=None, max_length=500)


class ChatMessage(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str = Field(max_length=4000)


class ChatIn(BaseModel):
    token_id: int
    messages: list[ChatMessage] = Field(max_length=40)


class ConfirmIn(BaseModel):
    tx_hash: str = Field(pattern="^0x[0-9a-fA-F]{64}$")


class EventIn(BaseModel):
    slug: str = Field(pattern="^[a-z0-9-]{3,80}$")
    title: str
    description: str = ""
    starts_at: datetime
    ends_at: datetime | None = None
    kind: str = "online"
    visibility: str = Field(default="holder", pattern="^(public|holder)$")
    official: bool = True
    capacity: int | None = None
    prize_text: str | None = None
    link: str | None = None


class QuestIn(BaseModel):
    slug: str = Field(pattern="^[a-z0-9-]{3,80}$")
    title: str
    description: str = ""
    verify_type: str = Field(default="manual", pattern="^(manual|auto_buy|auto_event)$")
    event_id: int | None = None
    trait_requirement: dict | None = None
    achievement_slug: str
    achievement_name: str
    achievement_icon: str = "trophy"
    achievement_kind: str = Field(default="quest", pattern="^(quest|win|contribution)$")


class ReviewIn(BaseModel):
    approve: bool
