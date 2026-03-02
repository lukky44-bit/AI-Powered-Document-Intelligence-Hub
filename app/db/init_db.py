from app.db.session import engine
from app.db.base import Base
from app.models import user, file, chat, chat_message  # noqa: F401

# important: loads the models

Base.metadata.create_all(bind=engine)
