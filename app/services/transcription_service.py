import os
import whisper
from app.core.config import settings

model = whisper.load_model("base")


def _resolve_audio_path(file_ref: str) -> str:
    # 1) full/relative path passed directly
    if os.path.exists(file_ref):
        return file_ref

    # 2) exact filename in docs directory
    docs_candidate = os.path.join(settings.DOCS_DIR, file_ref)
    if os.path.exists(docs_candidate):
        return docs_candidate

    # 3) legacy fallback: prefix lookup by id
    for f in os.listdir(settings.DOCS_DIR):
        if f.startswith(file_ref):
            return os.path.join(settings.DOCS_DIR, f)

    raise FileNotFoundError("Audio file not found")


def transcribe_audio(file_ref: str):
    file_path = _resolve_audio_path(file_ref)
    ext = file_path.split(".")[-1].lower()

    if ext not in ["mp3", "wav", "m4a", "mp4"]:
        raise ValueError("Unsupported audio format")

    result = model.transcribe(file_path)
    return result["text"]
