from fastapi import APIRouter, UploadFile, File
from app.services.file_service import save_file

router = APIRouter()


@router.post("/file")
async def upload_file(file: UploadFile = File(...)):
    data = save_file(file)
    return {
        "message": "File uploaded successfully",
        "file_id": data["file_id"],
        "filename": data["filename"],
    }
