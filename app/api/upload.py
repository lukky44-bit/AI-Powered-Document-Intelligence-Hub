from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Form, Request
from sqlalchemy.orm import Session

from app.services.file_service import save_file
from app.services.file_metadata_service import save_file_metadata
from app.services.ocr_service import extract_text
from app.services.transcription_service import transcribe_audio
from app.services.embedding_service import store_text
from app.services.pdf_service import extract_text_from_pdf
from app.services.docx_service import extract_text_from_docx
from app.services.file_cleanup_service import delete_uploaded_file

from app.db.session import get_db
from app.core.security import get_current_user
from app.core.rbac import ROLE_DOMAIN_MAP
from app.core.rate_limiter import limiter

router = APIRouter()


@router.post("/file")
@limiter.limit("2/minute")
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    file_domain: str | None = Form(None),  # optional
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user_role = current_user["role"]

    # ---------- DOMAIN DECISION ----------
    if user_role == "admin":
        if not file_domain:
            raise HTTPException(
                status_code=400,
                detail="Admin must specify file domain",
            )
        final_domain = file_domain
    else:
        domain_list = ROLE_DOMAIN_MAP.get(user_role)
        if not domain_list:
            raise HTTPException(
                status_code=400,
                detail="Invalid role for file upload",
            )
        final_domain = domain_list[0]

    # ---------- SAVE FILE ----------
    data = save_file(file)

    save_file_metadata(
        db=db,
        file_id=data["file_id"],
        filename=data["filename"],
        path=data["path"],
        domain=final_domain,
        uploaded_by=current_user["email"],
    )

    ext = data["extension"]
    text = ""

    try:
        if ext == "pdf":
            text = extract_text_from_pdf(data["path"])
            if not text.strip():
                text = extract_text(data["file_id"])

        elif ext in ["png", "jpg", "jpeg"]:
            text = extract_text(data["file_id"])

        elif ext == "docx":
            text = extract_text_from_docx(data["path"])

        elif ext in ["mp3", "wav", "m4a", "mp4"]:
            text = transcribe_audio(data["file_id"])

        else:
            raise ValueError("Unsupported file type for indexing")

        store_text(text, data["file_id"])

        # remove physical file after embeddings
        delete_uploaded_file(data["path"])

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "message": "File uploaded, processed and indexed successfully",
        "file_id": data["file_id"],
        "filename": data["filename"],
        "domain": final_domain,
        "uploaded_by": current_user["email"],
    }
