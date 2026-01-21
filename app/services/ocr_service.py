import os
import pytesseract
from PIL import Image
from pdf2image import convert_from_path
from app.core.config import settings


def extract_text(file_id: str):
    folder = settings.DOCS_DIR
    files = os.listdir(folder)

    target = None
    for f in files:
        if f.startswith(file_id):
            target = f
            break

    if not target:
        raise FileNotFoundError("File not found")

    file_path = os.path.join(folder, target)
    ext = target.split(".")[-1].lower()

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
