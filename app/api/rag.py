from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from app.services.rag_service import generate_rag_answer
from app.services.file_metadata_service import get_file_by_file_id
from app.db.session import get_db
from app.core.security import get_current_user
from app.core.rbac import ROLE_MODE_MAP, ROLE_DOMAIN_MAP

router = APIRouter()


@router.post("/answer")
def rag_answer(
    data: dict,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    try:
        query = data["query"]
        top_k = data.get("top_k", 3)
        file_id = data.get("file_id")
        mode = data.get("mode", "general")

        user_role = current_user["role"]

        # ---------- MODE RBAC ----------
        allowed_modes = ROLE_MODE_MAP.get(user_role, [])
        if user_role != "admin" and mode not in allowed_modes:
            raise HTTPException(
                status_code=403,
                detail=f"Role '{user_role}' is not allowed to use '{mode}' mode",
            )

        # ---------- DOMAIN RBAC ----------
        # If a specific file is requested, check its domain
        if file_id:
            file_record = get_file_by_file_id(db, file_id)
            if not file_record:
                raise HTTPException(status_code=404, detail="File not found")

            allowed_domains = ROLE_DOMAIN_MAP.get(user_role, [])
            if user_role != "admin" and file_record.domain not in allowed_domains:
                raise HTTPException(
                    status_code=403,
                    detail=f"Role '{user_role}' is not allowed to access '{file_record.domain}' documents",
                )

        # ---------- RAG GENERATION ----------
        answer, docs = generate_rag_answer(query, top_k, file_id, mode)

        # ---------- SOURCE ATTRIBUTION WITH DOMAIN CHECK ----------
        sources = []
        for d in docs:
            fid = d["metadata"]["doc_id"]
            chunk_id = d["metadata"]["chunk_id"]

            file_record = get_file_by_file_id(db, fid)
            if not file_record:
                continue

            # Enforce domain RBAC again for safety
            allowed_domains = ROLE_DOMAIN_MAP.get(user_role, [])
            if user_role != "admin" and file_record.domain not in allowed_domains:
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
                detail="No accessible sources found for your role",
            )

        return {
            "query": query,
            "mode": mode,
            "role": user_role,
            "answer": answer,
            "sources": sources,
            "user": current_user["email"],
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
