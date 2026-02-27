from app.db.session import engine
from app.db.base import Base
from app.models import user, file  # noqa: F401

# important: loads the models

Base.metadata.create_all(bind=engine)
