from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import get_current_user
from app.models.file import File
from app.services.embedding_service import delete_file_embeddings

router = APIRouter(prefix="/files", tags=["Files"])


@router.get("/my")
def get_my_files(
    db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)
):
    email = current_user["email"]

    files = (
        db.query(File)
        .filter(File.uploaded_by == email)
        .order_by(File.uploaded_at.desc())
        .all()
    )

    return {
        "count": len(files),
        "files": [
            {
                "file_id": f.file_id,
                "filename": f.filename,
                "domain": f.domain,
                "uploaded_at": f.uploaded_at,
            }
            for f in files
        ],
    }


@router.delete("/{file_id}")
def delete_file(
    file_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    # fetch file
    file = db.query(File).filter(File.file_id == file_id).first()
    if not file:
        raise HTTPException(status_code=404, details="File not found")

    user_roles = current_user["roles"]
    user_email = current_user["email"]

    if "admin" not in user_roles and file.uploaded_by != user_email:
        raise HTTPException(
            status_code=403, detail="you are not allowed to delete this file"
        )

    try:
        delete_file_embeddings(file_id)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Vector DB cleanup failed: {str(e)}"
        )

    db.delete(file)
    db.commit()

    return {"message": "File deleted succcessfully", "file_id": file_id}
