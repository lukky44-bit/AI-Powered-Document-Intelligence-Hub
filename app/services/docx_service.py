from docx import Document


def extract_text_from_docx(path: str):
    doc = Document(path)
    text = "\n".join([p.text for p in doc.paragraphs])
    return text.strip()
