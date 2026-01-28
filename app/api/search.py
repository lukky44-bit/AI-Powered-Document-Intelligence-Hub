from fastapi import APIRouter, HTTPException, Depends
from app.services.embedding_service import similarity_search
from app.core.security import get_current_user


router = APIRouter()


@router.post("/search")
def similarity_serach(data: dict, current_user: dict = Depends(get_current_user)):
    try:
        query = data["query"]
        top_k = data.get("top_k", 3)
        file_id = data.get["file_id"]
        result = similarity_search(query, top_k, file_id)
        return {"results": result, "file_id": file_id, "user": current_user}
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))
