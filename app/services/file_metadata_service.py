from sqlalchemy.orm import Session
from app.models.file import File


def save_file_metadata(db: Session, file_id, filename, path, uploaded_by, domain):
    file = File(
        file_id=file_id,
        filename=filename,
        path=path,
        uploaded_by=uploaded_by,
        domain=domain,
    )
    db.add(file)
    db.commit()
    db.refresh(file)
    return file


def get_file_by_file_id(db: Session, file_id: str):
    return db.query(File).filter(File.file_id == file_id).first()
