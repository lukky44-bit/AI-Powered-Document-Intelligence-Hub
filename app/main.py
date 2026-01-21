from fastapi import FastAPI
from app.core.config import settings
from app.api.auth import router as auth_router

app = FastAPI(title=settings.PROJECT_NAME)
app.include_router(auth_router, prefix="/auth", tags=["Auth"])


@app.get("/")
def root():
    return {"meesage": "AI Hub Project"}
