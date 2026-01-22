import os
import whisper
from app.core.config import settings

model = whisper.load_model("base")


def transcribe_audio(file_id: str):
    files = os.listdir(settings.DOCS_DIR)

    target = None
    for f in files:
        if f.startswith(file_id):
            target = f
            break

    if not target:
        raise FileNotFoundError("Audio file not found")

    file_path = os.path.join(settings.DOCS_DIR, target)
    ext = target.split(".")[-1].lower()

    if ext not in ["mp3", "wav", "m4a", "mp4"]:
        raise ValueError("Unsupported audio format")

    result = model.transcribe(file_path)
    return result["text"]
