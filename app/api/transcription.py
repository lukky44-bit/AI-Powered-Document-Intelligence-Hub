from fastapi import APIRouter, HTTPException
from app.services.transcription_service import transcribe_audio

router = APIRouter()


@router.post("/audio")
def transcribe(data: dict):
    try:
        text = transcribe_audio(data["file_id"])
        return {"transcription": text}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
