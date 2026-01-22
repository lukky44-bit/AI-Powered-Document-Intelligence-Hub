from fastapi import APIRouter, UploadFile, File, Depends
from app.services.file_service import save_file
from app.core.security import get_current_user

router = APIRouter()


@router.post("/file")
async def upload_file(
    file: UploadFile = File(...), current_user: str = Depends(get_current_user)
):
    data = save_file(file)
    return {
        "message": "File uploaded successfully",
        "file_id": data["file_id"],
        "filename": data["filename"],
        "uploaded_by": current_user,
    }
