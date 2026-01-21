import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    PROJECT_NAME = "Document AI Hub"
    PROJECT_NAME = "Document AI Hub"
    JWT_SECRET = os.getenv("JWT_SECRET", "supersecret")
    JWT_ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 60

    GROQ_API_KEY = os.getenv("GROQ_API_KEY")

    DATABASE_URL = os.getenv(
        "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/document_ai"
    )

    DATA_DIR = "data"
    DOCS_DIR = f"{DATA_DIR}/documents"
    EMBEDDINGS_DIR = f"{DATA_DIR}/embeddings"


settings = Settings()
