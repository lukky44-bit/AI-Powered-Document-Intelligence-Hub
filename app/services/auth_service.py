from sqlalchemy.orm import Session
from app.models.user import User
from app.core.security import hash_password, verify_password, create_access_token


def create_user(db: Session, username: str, password: str, email: str):
    # Ensure password is a string before hashing to avoid type errors
    password_str = str(password)
    user = User(
        username=username, email=email, hashed_password=hash_password(password_str)
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return None
    elif not verify_password(password, user.hashed_password):
        return None
    else:
        return user


def login_user(db: Session, email: str, password: str):
    user = authenticate_user(db, email, password)
    if not user:
        return None
    token = create_access_token({"sub": user.email})
    return token
