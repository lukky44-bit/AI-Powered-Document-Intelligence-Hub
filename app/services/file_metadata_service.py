from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.models.file import File
from app.core.rbac import get_allowed_domains, has_admin_role


def save_file_metadata(db: Session, file_id, filename, path, uploaded_by, domain):
    try:
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
    except SQLAlchemyError as e:
        db.rollback()
        raise Exception(f"Database error while saving file metadata: {str(e)}")


def get_file_by_file_id(db: Session, file_id: str):
    return db.query(File).filter(File.file_id == file_id).first()


def get_file_by_filename(db: Session, filename: str):
    return db.query(File).filter(File.filename == filename).first()


def get_accessible_file_ids(
    db: Session,
    user_email: str,
    user_roles: list[str],
    domain: str | None = None,
) -> list[str]:
    """Return file_ids that a user can access, optionally scoped by domain."""
    query = db.query(File.file_id)

    if domain:
        query = query.filter(File.domain == domain)

    if not has_admin_role(user_roles):
        allowed_domains = get_allowed_domains(user_roles) or []
        query = query.filter(
            (File.uploaded_by == user_email) | (File.domain.in_(allowed_domains))
        )

    rows = query.all()
    return [row.file_id for row in rows]
