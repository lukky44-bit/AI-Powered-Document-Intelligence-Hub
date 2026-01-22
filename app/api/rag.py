from fastapi import APIRouter, HTTPException
from app.services.rag_service import generate_rag_answer

router = APIRouter()


@router.post("/answer")
def rag_answer(data: dict):
    try:
        query = data["query"]
        top_k = data.get("top_k", 3)
        result = generate_rag_answer(query, top_k)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
