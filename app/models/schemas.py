from pydantic import BaseModel
from uuid import UUID
from datetime import datetime


class ChatCreate(BaseModel):
    title: str | None = None


class ChatResponse(BaseModel):
    id: UUID
    title: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    id: UUID
    role: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True
