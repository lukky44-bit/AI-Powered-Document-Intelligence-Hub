from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from uuid import UUID
from datetime import datetime
from app.db.session import get_db
from app.models.chat import Chat
from app.models.chat_message import ChatMessage
from app.core.security import get_current_user
from app.core.rbac import can_access_mode, has_admin_role
from app.services.rag_service import generate_rag_answer, summarize_messages
from app.services.file_metadata_service import (
    get_accessible_file_ids,
    get_file_by_file_id,
)

router = APIRouter(prefix="/chats", tags=["Chats"])

MODE_DOMAIN_MAP = {
    "legal": "legal",
    "finance": "finance",
    "academic": "academic",
    "healthcare": "healthcare",
    "business": "business",
}


def get_or_create_message_records(db: Session, chat_id: UUID, user_email: str):
    """Get or create the two ChatMessage records (user_messages and assistant_messages)."""
    user_msgs = (
        db.query(ChatMessage)
        .filter(ChatMessage.chat_id == chat_id, ChatMessage.role == "user_messages")
        .first()
    )

    if not user_msgs:
        user_msgs = ChatMessage(
            chat_id=chat_id, user_email=user_email, role="user_messages", messages=[]
        )
        db.add(user_msgs)

    assistant_msgs = (
        db.query(ChatMessage)
        .filter(
            ChatMessage.chat_id == chat_id, ChatMessage.role == "assistant_messages"
        )
        .first()
    )

    if not assistant_msgs:
        assistant_msgs = ChatMessage(
            chat_id=chat_id,
            user_email=user_email,
            role="assistant_messages",
            messages=[],
        )
        db.add(assistant_msgs)

    db.commit()
    db.refresh(user_msgs)
    db.refresh(assistant_msgs)

    return user_msgs, assistant_msgs


def get_all_messages(user_msgs: ChatMessage, assistant_msgs: ChatMessage):
    """Merge and sort messages from both records."""
    all_msgs = []

    for msg in user_msgs.messages or []:
        all_msgs.append(
            {"role": "user", "content": msg["content"], "timestamp": msg["timestamp"]}
        )

    for msg in assistant_msgs.messages or []:
        all_msgs.append(
            {
                "role": "assistant",
                "content": msg["content"],
                "timestamp": msg["timestamp"],
            }
        )

    # Sort by timestamp
    all_msgs.sort(key=lambda x: x["timestamp"])
    return all_msgs


def compress_chat_history(
    db: Session, chat: Chat, user_msgs: ChatMessage, assistant_msgs: ChatMessage
) -> None:
    """Compress chat history when total messages exceed 6."""
    total_messages = len(user_msgs.messages or []) + len(assistant_msgs.messages or [])

    if total_messages <= 6:
        return

    all_msgs = get_all_messages(user_msgs, assistant_msgs)

    if len(all_msgs) <= 6:
        return

    # Take oldest 4 messages for summarization
    oldest_messages = all_msgs[:4]

    summary_input = []
    if chat.summary:
        summary_input.append(
            {
                "role": "system",
                "content": f"Previous summary:\n{chat.summary}",
            }
        )

    for msg in oldest_messages:
        summary_input.append(msg)

    new_summary = summarize_messages(summary_input)

    if not new_summary:
        return

    chat.summary = new_summary

    # Remove oldest 4 messages from the JSONB arrays
    oldest_timestamps = {msg["timestamp"] for msg in oldest_messages}

    user_msgs.messages = [
        msg
        for msg in (user_msgs.messages or [])
        if msg["timestamp"] not in oldest_timestamps
    ]
    flag_modified(user_msgs, "messages")

    assistant_msgs.messages = [
        msg
        for msg in (assistant_msgs.messages or [])
        if msg["timestamp"] not in oldest_timestamps
    ]
    flag_modified(assistant_msgs, "messages")

    db.commit()


@router.post("/")
def create_chat(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    chat = Chat(user_email=current_user["email"])
    db.add(chat)
    db.commit()
    db.refresh(chat)

    return {"chat_id": chat.id}


@router.get("/")
def list_chats(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    chats = (
        db.query(Chat)
        .filter(Chat.user_email == current_user["email"])
        .order_by(Chat.created_at.desc())
        .all()
    )

    return [
        {
            "chat_id": chat.id,
            "title": chat.title or str(chat.id)[:8],
            "created_at": chat.created_at,
        }
        for chat in chats
    ]


@router.get("/{chat_id}")
def get_chat_messages(
    chat_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    chat = (
        db.query(Chat)
        .filter(Chat.id == chat_id, Chat.user_email == current_user["email"])
        .first()
    )

    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    # Get the two message records
    user_msgs = (
        db.query(ChatMessage)
        .filter(ChatMessage.chat_id == chat_id, ChatMessage.role == "user_messages")
        .first()
    )

    assistant_msgs = (
        db.query(ChatMessage)
        .filter(
            ChatMessage.chat_id == chat_id, ChatMessage.role == "assistant_messages"
        )
        .first()
    )

    if not user_msgs or not assistant_msgs:
        return []

    # Merge and sort all messages
    all_msgs = get_all_messages(user_msgs, assistant_msgs)

    return [
        {
            "role": msg["role"],
            "content": msg["content"],
            "created_at": msg["timestamp"],
        }
        for msg in all_msgs
    ]


@router.post("/{chat_id}/message")
def send_message(
    chat_id: UUID,
    data: dict,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    chat = (
        db.query(Chat)
        .filter(Chat.id == chat_id, Chat.user_email == current_user["email"])
        .first()
    )

    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    user_message = data.get("message")
    mode = data.get("mode", "general")
    response_format = data.get("format", "text")
    top_k = data.get("top_k", 15)
    file_id = data.get("file_id")

    user_roles = current_user["roles"]
    user_email = current_user["email"]

    if not has_admin_role(user_roles) and not can_access_mode(user_roles, mode):
        raise HTTPException(
            status_code=403,
            detail=f"Your roles do not allow access to '{mode}' mode",
        )

    scoped_domain = MODE_DOMAIN_MAP.get(mode)

    if file_id:
        file_record = get_file_by_file_id(db, file_id)
        if not file_record:
            raise HTTPException(status_code=404, detail="File not found")

        if not has_admin_role(user_roles) and file_record.uploaded_by != user_email:
            raise HTTPException(
                status_code=403,
                detail="You are not allowed to access this file",
            )

        if scoped_domain and file_record.domain != scoped_domain:
            raise HTTPException(
                status_code=403,
                detail=(
                    f"Mode '{mode}' only allows documents in '{scoped_domain}' domain"
                ),
            )

    allowed_file_ids = None
    if not file_id:
        allowed_file_ids = get_accessible_file_ids(
            db=db,
            user_email=user_email,
            user_roles=user_roles,
            domain=scoped_domain,
        )

    # Get or create the two message records
    user_msgs, assistant_msgs = get_or_create_message_records(db, chat_id, user_email)

    # 1️⃣ Save user message to JSONB array
    timestamp = datetime.utcnow().isoformat()
    if user_msgs.messages is None:
        user_msgs.messages = []

    user_msgs.messages.append({"content": user_message, "timestamp": timestamp})
    flag_modified(user_msgs, "messages")  # Mark JSONB field as modified

    # If chat has no title, generate one
    if not chat.title:
        short_title = user_message[:50]
        chat.title = short_title

    db.commit()

    # 2️⃣ Get recent messages for prompt context
    all_msgs = get_all_messages(user_msgs, assistant_msgs)
    recent_messages = all_msgs[-4:] if len(all_msgs) > 4 else all_msgs

    # 3️⃣ Generate RAG response with history
    answer, docs = generate_rag_answer(
        query=user_message,
        top_k=top_k,
        file_id=file_id,
        allowed_file_ids=allowed_file_ids,
        mode=mode,
        response_format=response_format,
        conversation_summary=chat.summary,
        recent_messages=recent_messages,
    )

    # 4️⃣ Save assistant response to JSONB array
    timestamp = datetime.utcnow().isoformat()
    if assistant_msgs.messages is None:
        assistant_msgs.messages = []

    assistant_msgs.messages.append({"content": answer, "timestamp": timestamp})
    flag_modified(assistant_msgs, "messages")  # Mark JSONB field as modified

    # 5️⃣ Compress older messages into chat.summary when needed
    try:
        compress_chat_history(db, chat, user_msgs, assistant_msgs)
    except Exception:
        # Keep chat history safe: if summarization fails, don't delete messages.
        db.rollback()
        assistant_msgs.messages.append({"content": answer, "timestamp": timestamp})
        flag_modified(assistant_msgs, "messages")

    db.commit()

    return {
        "chat_id": chat_id,
        "answer": answer,
        "sources": [
            {
                "file_id": d["metadata"]["doc_id"],
                "chunk_id": d["metadata"]["chunk_id"],
                "text": d["text"],
            }
            for d in docs
        ],
    }
