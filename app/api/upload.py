from fastapi import APIRouter, UploadFile, File, Depends
from sqlalchemy.orm import Session
from app.services.file_service import save_file
from app.services.file_metadata_service import save_file_metadata
from app.db.session import get_db
from app.core.security import get_current_user

router = APIRouter()


@router.post("/file")
async def upload_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    data = save_file(file)

    save_file_metadata(
        db=db,
        file_id=data["file_id"],
        filename=data["filename"],
        path=data["path"],
        uploaded_by=current_user,
    )

    return {
        "message": "File uploaded and metadata stored",
        "file_id": data["file_id"],
        "filename": data["filename"],
        "uploaded_by": current_user,
    }
