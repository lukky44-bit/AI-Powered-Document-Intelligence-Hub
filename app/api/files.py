from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import get_current_user
from app.models.file import File  # assuming model name is File

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
