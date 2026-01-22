from fastapi import APIRouter, HTTPException
from app.services.embedding_service import similarity_search


router = APIRouter()


@router.post("/search")
def similarity_serach(data: dict):
    try:
        query = data["query"]
        top_k = data.get("top_k", 3)
        result = similarity_search(query, top_k)
        return {"results": result}
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))
