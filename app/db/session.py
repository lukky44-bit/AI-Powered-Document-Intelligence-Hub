from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Configure engine with proper settings for concurrent writes
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,  # Verify connections before using them
    pool_size=10,  # Increase connection pool size
    max_overflow=20,  # Allow temporary connections beyond pool_size
    pool_recycle=3600,  # Recycle connections after 1 hour
    echo=False,  # Set to True for debugging SQL queries
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
