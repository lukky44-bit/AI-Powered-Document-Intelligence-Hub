from fastapi import FastAPI
from app.core.config import settings
from app.api.auth import router as auth_router
from app.api.upload import router as upload_router
from app.api.ocr import router as ocr_router
from app.api.transcription import router as transcription_router
from app.api.embeddings import router as embeddings_router
from app.api.search import router as search_router
from app.api.rag import router as rag_router


app = FastAPI(title=settings.PROJECT_NAME)
app.include_router(auth_router, prefix="/auth", tags=["Auth"])
app.include_router(upload_router, prefix="/upload", tags=["Upload"])
app.include_router(ocr_router, prefix="/ocr", tags=["OCR"])
app.include_router(
    transcription_router, prefix="/transcription", tags=["Transcription"]
)
app.include_router(embeddings_router, prefix="/embeddings", tags=["Embeddings"])
app.include_router(search_router, prefix="/search", tags=["Search"])

app.include_router(rag_router, prefix="/rag", tags=["RAG"])


@app.get("/")
def root():
    return {"message": "AI Hub Project"}
