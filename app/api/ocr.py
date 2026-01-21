from fastapi import APIRouter, HTTPException
from app.services.ocr_service import extract_text

router = APIRouter()


@router.post("/extract")
def ocr_extract(data: dict):
    try:
        text = extract_text(data["file_id"])
        return {"extracted_text": text}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
