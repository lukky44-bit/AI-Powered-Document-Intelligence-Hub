from fastapi import APIRouter, HTTPException
import uuid
from app.services.embedding_service import store_text

router = APIRouter()


@router.post("/store")
def store_embeddings(data: dict):
    try:
        text = data["text"]
        doc_id = str(uuid.uuid4())
        result = store_text(text, doc_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
