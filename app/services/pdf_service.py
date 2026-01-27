from pypdf import PdfReader


def extract_text_from_pdf(path: str):
    reader = PdfReader(path)
    text = ""
    for page in reader.pages:
        t = page.extract_text()
        if t:
            text += t + "\n"
    return text.strip()
