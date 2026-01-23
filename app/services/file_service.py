import os
import uuid
from app.core.config import settings


def save_file(file):
    os.makedirs(settings.DOCS_DIR, exist_ok=True)

    file_id = str(uuid.uuid4())
    filename = f"{file_id}_{file.filename}"
    file_path = os.path.join(settings.DOCS_DIR, filename)

    with open(file_path, "wb") as f:
        f.write(file.file.read())
    ext = filename.split(".")[-1].lower()

    return {
        "file_id": file_id,
        "filename": filename,
        "path": file_path,
        "extension": ext,
    }
