from fastapi import FastAPI
from app.core.config import settings
from app.api.auth import router as auth_router
from app.api.upload import router as upload_router
from app.api.ocr import router as ocr_router


app = FastAPI(title=settings.PROJECT_NAME)
app.include_router(auth_router, prefix="/auth", tags=["Auth"])
app.include_router(upload_router, prefix="/upload", tags=["Upload"])
app.include_router(ocr_router, prefix="/ocr", tags=["OCR"])


@app.get("/")
def root():
    return {"meesage": "AI Hub Project"}
