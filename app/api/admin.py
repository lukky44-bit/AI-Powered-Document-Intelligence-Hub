from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.core.security import get_current_user

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.put("/users/roles")
def update_user_roles(
    data: dict,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    email = data.get("email")
    new_roles = data.get("roles")  # Expect a list of roles

    # ---------- ADMIN CHECK ----------
    if "admin" not in current_user["roles"]:
        raise HTTPException(status_code=403, detail="Admin access required")

    # ---------- FIND USER ----------
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # ---------- VALIDATE ROLES ----------
    if not isinstance(new_roles, list) or len(new_roles) == 0:
        raise HTTPException(status_code=400, detail="Roles must be a non-empty list")

    allowed_roles = ["researcher", "doctor", "lawyer", "finance", "business", "admin"]
    for role in new_roles:
        if role not in allowed_roles:
            raise HTTPException(status_code=400, detail=f"Invalid role: {role}")

    # ---------- UPDATE ----------
    user.roles = new_roles
    db.commit()
    db.refresh(user)

    return {
        "message": "User roles updated successfully",
        "email": user.email,
        "roles": user.roles,
    }
