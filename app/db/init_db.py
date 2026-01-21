from app.db.session import engine
from app.db.base import Base
from app.models.user import User  # important: loads the model

Base.metadata.create_all(bind=engine)
