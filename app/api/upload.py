from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Form
from sqlalchemy.orm import Session

from app.services.file_service import save_file
from app.services.file_metadata_service import save_file_metadata
from app.services.ocr_service import extract_text
from app.services.transcription_service import transcribe_audio
from app.services.embedding_service import store_text

from app.db.session import get_db
from app.core.security import get_current_user
from app.services.pdf_service import extract_text_from_pdf
from app.services.docx_service import extract_text_from_docx
from app.core.rbac import ROLE_DOMAIN_MAP


router = APIRouter()


@router.post("/file")
async def upload_file(
    file: UploadFile = File(...),
    file_domain: str = Form(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user_role = current_user["role"]

    if user_role != "admin":
        allowed_domains = ROLE_DOMAIN_MAP.get(user_role, [])
        if file_domain not in allowed_domains:
            raise HTTPException(
                status_code=403,
                detail=f"Role '{user_role}' cannot upload '{file_domain}' documents",
            )
    data = save_file(file)

    save_file_metadata(
        db=db,
        file_id=data["file_id"],
        filename=data["filename"],
        path=data["path"],
        uploaded_by=current_user["email"],
        domain=file_domain,
    )

    ext = data["extension"]
    text = ""

    try:
        if ext in ["pdf"]:
            text = extract_text_from_pdf(data["path"])
            if not text.strip():
                text = extract_text(data["file_id"])
        elif ext in ["png", "jpg", "jpeg"]:
            text = extract_text(data["file_id"])
        elif ext in ["docx"]:
            text = extract_text_from_docx(data["path"])
        elif ext in ["mp3", "wav", "m4a", "mp4"]:
            text = transcribe_audio(data["file_id"])
        else:
            raise ValueError("Unsupported file type for indexing")

        store_text(text, data["file_id"])

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "message": "File uploaded, processed and indexed successfully",
        "file_id": data["file_id"],
        "filename": data["filename"],
        "uploaded_by": current_user,
    }
