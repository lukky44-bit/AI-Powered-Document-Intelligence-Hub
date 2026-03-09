from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.base import Base


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(UUID(as_uuid=True), ForeignKey("chats.id"))
    user_email = Column(String, nullable=False)
    role = Column(String, nullable=False)  # "user_messages" or "assistant_messages"
    messages = Column(
        JSONB, nullable=False, default=list
    )  # Array of {content: str, timestamp: datetime}
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    chat = relationship("Chat", back_populates="messages")
