from sqlalchemy.orm import Session
from app.models.file import File


def save_file_metadata(db: Session, file_id, filename, path, uploaded_by):
    file = File(file_id=file_id, filename=filename, path=path, uploaded_by=uploaded_by)
    db.add(file)
    db.commit()
    db.refresh(file)
    return file
