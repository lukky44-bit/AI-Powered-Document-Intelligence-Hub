from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.core.security import get_current_user

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.put("/users/role")
def update_user_role(
    data: dict,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    email = data.get("email")
    new_role = data.get("new_role")
    # ---------- ADMIN CHECK ----------
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    # ---------- FIND USER ----------
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # ---------- VALIDATE ROLE ----------
    allowed_roles = ["researcher", "doctor", "lawyer", "finance", "business", "admin"]
    if new_role not in allowed_roles:
        raise HTTPException(status_code=400, detail="Invalid role")

    # ---------- UPDATE ----------
    user.role = new_role
    db.commit()
    db.refresh(user)

    return {
        "message": "User role updated successfully",
        "email": user.email,
        "new_role": user.role,
    }
