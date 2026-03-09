from fastapi import APIRouter, HTTPException, Depends
from app.services.transcription_service import transcribe_audio
from app.services.file_metadata_service import get_file_by_file_id
from app.db.session import get_db
from sqlalchemy.orm import Session

router = APIRouter()


@router.post("/audio")
def transcribe(data: dict, db: Session = Depends(get_db)):
    try:
        file_id = data["file_id"]
        file_record = get_file_by_file_id(db, file_id)
        if not file_record:
            raise HTTPException(status_code=404, detail="File not found")

        text = transcribe_audio(file_record.path)
        return {"transcription": text}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
