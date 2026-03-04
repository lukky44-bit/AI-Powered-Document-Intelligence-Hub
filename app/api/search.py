from fastapi import APIRouter, HTTPException, Depends
from app.services.embedding_service import similarity_search as search_embeddings
from app.services.file_metadata_service import (
    get_file_by_file_id,
    get_accessible_file_ids,
)
from app.db.session import get_db
from app.core.security import get_current_user
from app.core.rbac import has_admin_role
from sqlalchemy.orm import Session


router = APIRouter()


@router.post("/search")
def similarity_search(
    data: dict,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    try:
        query = data["query"]
        top_k = data.get("top_k", 3)
        file_id = data.get("file_id")
        user_roles = current_user["roles"]
        user_email = current_user["email"]

        # ---------- OWNERSHIP CHECK ----------
        if file_id:
            file_record = get_file_by_file_id(db, file_id)
            if not file_record:
                raise HTTPException(status_code=404, detail="File not found")

            if not has_admin_role(user_roles) and file_record.uploaded_by != user_email:
                raise HTTPException(
                    status_code=403,
                    detail="You are not allowed to access this file",
                )

        allowed_file_ids = None
        if not file_id and not has_admin_role(user_roles):
            allowed_file_ids = get_accessible_file_ids(
                db=db,
                user_email=user_email,
                user_roles=user_roles,
            )

        result = search_embeddings(query, top_k, file_id, allowed_file_ids)
        return {"results": result, "file_id": file_id, "user": current_user["email"]}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
