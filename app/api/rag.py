from fastapi import APIRouter, HTTPException, Depends, Request
from sqlalchemy.orm import Session

from app.services.rag_service import generate_rag_answer
from app.services.file_metadata_service import (
    get_file_by_filename,
    get_file_by_file_id,
    get_accessible_file_ids,
)
from app.db.session import get_db
from app.core.security import get_current_user
from app.core.rbac import can_access_mode, has_admin_role
from app.core.rate_limiter import limiter

router = APIRouter()

MODE_DOMAIN_MAP = {
    "legal": "legal",
    "finance": "finance",
    "academic": "academic",
    "healthcare": "healthcare",
    "business": "business",
}


@router.post("/answer")
@limiter.limit("10/minute")
def rag_answer(
    request: Request,
    data: dict,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    try:
        # ---------- INPUT ----------
        query = data["query"]
        top_k = data.get("top_k", 3)
        filename = data.get("filename")
        file_id = data.get("file_id")
        mode = data.get("mode", "general")
        response_format = data.get("format", "")

        user_roles = current_user["roles"]
        user_email = current_user["email"]

        # ---------- MODE RBAC ----------
        if not has_admin_role(user_roles) and not can_access_mode(user_roles, mode):
            raise HTTPException(
                status_code=403,
                detail=f"Your roles do not allow access to '{mode}' mode",
            )

        # ---------- FILENAME / FILE_ID RESOLUTION ----------
        file_record = None
        scoped_domain = MODE_DOMAIN_MAP.get(mode)

        if filename:
            file_record = get_file_by_filename(db, filename)
            if not file_record:
                raise HTTPException(status_code=404, detail="File not found")

        elif file_id:
            file_record = get_file_by_file_id(db, file_id)
            if not file_record:
                raise HTTPException(status_code=404, detail="File not found")

        # ---------- DOMAIN + OWNERSHIP RBAC ----------
        if file_record:
            if not has_admin_role(user_roles) and file_record.uploaded_by != user_email:
                raise HTTPException(
                    status_code=403,
                    detail="You are not allowed to access this file",
                )

            if scoped_domain and file_record.domain != scoped_domain:
                raise HTTPException(
                    status_code=403,
                    detail=(
                        f"Mode '{mode}' only allows documents in '{scoped_domain}' "
                        "domain"
                    ),
                )

            # enforce file scoping
            file_id = file_record.file_id

        allowed_file_ids = None
        if not file_id:
            allowed_file_ids = get_accessible_file_ids(
                db=db,
                user_email=user_email,
                user_roles=user_roles,
                domain=scoped_domain,
            )

        # ---------- RAG GENERATION ----------
        answer, docs = generate_rag_answer(
            query=query,
            top_k=top_k,
            file_id=file_id,
            allowed_file_ids=allowed_file_ids,
            mode=mode,
            response_format=response_format,
        )

        # ---------- SOURCE ATTRIBUTION + SAFETY ----------
        sources = []

        for d in docs:
            fid = d["metadata"]["doc_id"]
            chunk_id = d["metadata"]["chunk_id"]

            file = get_file_by_file_id(db, fid)
            if not file:
                continue

            # Skip files the user doesn't own (non-admin)
            if not has_admin_role(user_roles) and file.uploaded_by != user_email:
                continue

            sources.append(
                {
                    "file_id": fid,
                    "filename": file.filename,
                    "domain": file.domain,
                    "chunk_id": chunk_id,
                    "text": d["text"],
                }
            )

        # If no accessible sources found, return a helpful message instead of error
        if not sources:
            answer_msg = (
                "No accessible documents found for your query. This could mean: "
                "(1) No documents match your search, (2) The relevant documents "
                "belong to domains you don't have access to, or (3) No files "
                "have been uploaded yet."
            )
            return {
                "query": query,
                "mode": mode,
                "roles": user_roles,
                "answer": answer_msg,
                "sources": [],
                "user": user_email,
            }

        return {
            "query": query,
            "mode": mode,
            "roles": user_roles,
            "answer": answer,
            "sources": sources,
            "user": user_email,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
