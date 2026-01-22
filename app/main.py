from fastapi import FastAPI
from app.core.config import settings
from app.routes import register_routes

app = FastAPI(title=settings.PROJECT_NAME)

register_routes(app)


@app.get("/")
def root():
    return {"message": "Document AI Hub is running"}
