from fastapi import APIRouter, HTTPException, Depends
import uuid
from app.services.embedding_service import store_text
from app.core.security import get_current_user

router = APIRouter()


@router.post("/store")
def store_embeddings(data: dict, current_user: str = Depends(get_current_user)):
    try:
        text = data["text"]
        doc_id = str(uuid.uuid4())
        result = store_text(text, doc_id)
        result["uploaded_by"] = current_user
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
