from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from app.db.base import Base


class File(Base):
    __tablename__ = "files"

    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(String, unique=True, index=True)
    filename = Column(String)
    path = Column(String)
    uploaded_by = Column(String)
    domain = Column(String)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
