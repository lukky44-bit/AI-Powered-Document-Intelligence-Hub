from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID
from app.db.session import get_db
from app.models.chat import Chat
from app.models.chat_message import ChatMessage
from app.core.security import get_current_user
from app.core.rbac import can_access_mode, has_admin_role
from app.services.rag_service import generate_rag_answer
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

    return [
        {
            "id": msg.id,
            "role": msg.role,
            "content": msg.content,
            "created_at": msg.created_at,
        }
        for msg in chat.messages
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

    # 1️⃣ Save user message
    user_msg = ChatMessage(
        chat_id=chat_id,
        role="user",
        content=user_message,
    )
    # If chat has no title, generate one
    if not chat.title:
        short_title = user_message[:50]
        chat.title = short_title

    db.add(user_msg)
    db.commit()

    # 2️⃣ Get last 6 messages (sliding window)
    history = (
        db.query(ChatMessage)
        .filter(ChatMessage.chat_id == chat_id)
        .order_by(ChatMessage.created_at.desc())
        .limit(5)
        .all()
    )

    history = list(reversed(history))

    # 3️⃣ Generate RAG response with history
    answer, docs = generate_rag_answer(
        query=user_message,
        top_k=top_k,
        file_id=file_id,
        allowed_file_ids=allowed_file_ids,
        mode=mode,
        response_format=response_format,
        chat_history=history,
    )

    # 4️⃣ Save assistant response
    assistant_msg = ChatMessage(
        chat_id=chat_id,
        role="assistant",
        content=answer,
    )
    db.add(assistant_msg)
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
