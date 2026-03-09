import os
import pytesseract
from PIL import Image
from pdf2image import convert_from_path
from app.core.config import settings


def _resolve_file_path(file_ref: str) -> str:
    # 1) full/relative path passed directly
    if os.path.exists(file_ref):
        return file_ref

    # 2) exact filename under docs dir
    docs_candidate = os.path.join(settings.DOCS_DIR, file_ref)
    if os.path.exists(docs_candidate):
        return docs_candidate

    # 3) legacy fallback: prefix lookup (for older storage strategy)
    folder = settings.DOCS_DIR
    for f in os.listdir(folder):
        if f.startswith(file_ref):
            return os.path.join(folder, f)

    raise FileNotFoundError("File not found")


def extract_text(file_ref: str):
    file_path = _resolve_file_path(file_ref)
    ext = file_path.split(".")[-1].lower()

    text = ""

    if ext in ["png", "jpg", "jpeg"]:
        image = Image.open(file_path)
        text = pytesseract.image_to_string(image)

    elif ext == "pdf":
        pages = convert_from_path(file_path)
        for page in pages:
            text += pytesseract.image_to_string(page)

    else:
        raise ValueError("Unsupported file type for OCR")

    return text.strip()
