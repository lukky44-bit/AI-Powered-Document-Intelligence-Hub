from fastapi import APIRouter, HTTPException, Depends
from app.services.embedding_service import similarity_search
from app.services.file_metadata_service import get_file_by_file_id
from app.db.session import get_db
from app.core.security import get_current_user
from app.core.rbac import can_access_domain, has_admin_role
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

        # ---------- DOMAIN RBAC CHECK ----------
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

        result = similarity_search(query, top_k, file_id)
        return {"results": result, "file_id": file_id, "user": current_user["email"]}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
