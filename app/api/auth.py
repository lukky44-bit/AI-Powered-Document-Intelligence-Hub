from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.auth_service import create_user, login_user

router = APIRouter()


@router.post("/signup")
def signup(data: dict, db: Session = Depends(get_db)):
    user = create_user(
        db, username=data["username"], password=data["password"], email=data["email"]
    )
    return {"message": "User created Successfully", "Name": user.username}


@router.post("/login")
def login(data: dict, db: Session = Depends(get_db)):
    token = login_user(db, data["email"], data["password"])
    if not token:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    else:
        return {"token": token, "token_type": "bearer"}
