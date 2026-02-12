from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from app.services.rag_service import generate_rag_answer
from app.services.file_metadata_service import get_file_by_file_id
from app.db.session import get_db
from app.core.security import get_current_user
from app.core.rbac import can_access_mode, can_access_domain, has_admin_role
from app.core.rate_limiter import limiter
from fastapi import Request

router = APIRouter()


@router.post("/answer")
@limiter.limit("10/minute")
def rag_answer(
    request: Request,
    data: dict,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    try:
        query = data["query"]
        top_k = data.get("top_k", 3)
        file_id = data.get("file_id")
        mode = data.get("mode", "general")
        response_format = data.get("format", "")

        user_roles = current_user["roles"]

        # ---------- MODE RBAC ----------
        if not has_admin_role(user_roles) and not can_access_mode(user_roles, mode):
            raise HTTPException(
                status_code=403,
                detail=f"Your roles do not allow access to '{mode}' mode",
            )

        # ---------- DOMAIN RBAC ----------
        # If a specific file is requested, check its domain
        if file_id:
            file_record = get_file_by_file_id(db, file_id)
            if not file_record:
                raise HTTPException(status_code=404, detail="File not found")

            if not has_admin_role(user_roles) and not can_access_domain(
                user_roles, file_record.domain
            ):
                raise HTTPException(
                    status_code=403,
                    detail=f"Your roles do not allow access to '{file_record.domain}' documents",
                )

        # ---------- RAG GENERATION ----------
        answer, docs = generate_rag_answer(query, top_k, file_id, mode, response_format)

        # ---------- SOURCE ATTRIBUTION WITH DOMAIN CHECK ----------
        sources = []
        for d in docs:
            fid = d["metadata"]["doc_id"]
            chunk_id = d["metadata"]["chunk_id"]

            file_record = get_file_by_file_id(db, fid)
            if not file_record:
                continue

            # Enforce domain RBAC again for safety
            if not has_admin_role(user_roles) and not can_access_domain(
                user_roles, file_record.domain
            ):
                continue

            sources.append(
                {
                    "file_id": fid,
                    "filename": file_record.filename,
                    "domain": file_record.domain,
                    "chunk_id": chunk_id,
                    "text": d["text"],
                }
            )

        if not sources:
            raise HTTPException(
                status_code=403,
                detail="No accessible sources found ",
            )

        return {
            "query": query,
            "mode": mode,
            "roles": user_roles,
            "answer": answer,
            "sources": sources,
            "user": current_user["email"],
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
