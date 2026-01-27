from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.services.rag_service import generate_rag_answer
from app.services.file_metadata_service import get_file_by_file_id
from app.db.session import get_db
from app.core.security import get_current_user

router = APIRouter()


@router.post("/answer")
def rag_answer(
    data: dict,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    try:
        query = data["query"]
        top_k = data.get("top_k", 3)
        file_id = data.get("file_id")
        mode = data.get("mode", "general")

        answer, docs = generate_rag_answer(query, top_k, file_id, mode)

        sources = []
        for d in docs:
            fid = d["metadata"]["doc_id"]
            chunk_id = d["metadata"]["chunk_id"]

            file_record = get_file_by_file_id(db, fid)

            sources.append(
                {
                    "file_id": fid,
                    "filename": file_record.filename if file_record else None,
                    "chunk_id": chunk_id,
                    "text": d["text"],
                }
            )

        return {
            "query": query,
            "mode": mode,
            "answer": answer,
            "sources": sources,
            "user": current_user,
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
