from fastapi import APIRouter, HTTPException, Depends
from app.services.rag_service import generate_rag_answer
from app.core.security import get_current_user

router = APIRouter()


@router.post("/answer")
def rag_answer(data: dict, current_user: str = Depends(get_current_user)):
    try:
        query = data["query"]
        top_k = data.get("top_k", 3)
        file_id = data.get("file_id")
        result = generate_rag_answer(query, top_k, file_id)
        result["user"] = current_user

        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
