from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.auth.dependencies import require_admin, require_root
from app.auth.security import hash_password
from app.auth.routes import UserOut
from app.db.database import get_db
from app.db.models import User


router = APIRouter(prefix="/users", tags=["users"])


class RoleUpdate(BaseModel):
    role: str  # "admin" | "user"


class CreateUserRequest(BaseModel):
    email: EmailStr
    password: str
    role: str = "user"


def _can_manage(actor: User, target: User) -> bool:
    """Role hierarchy: root manages everyone (except root accounts);
    plain admins manage only regular users."""
    if target.role == "root":
        return False
    if actor.role == "root":
        return True
    return target.role == "user"


@router.post("", response_model=UserOut, status_code=201)
def create_user(
    request: CreateUserRequest,
    actor: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Admins can create regular users; ONLY root can create admins."""
    if request.role not in ("admin", "user"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Role must be 'admin' or 'user'")
    if request.role == "admin" and actor.role != "root":
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Only the root account can create administrator accounts",
        )
    if len(request.password) < 8:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Password must be at least 8 characters")

    existing = db.query(User).filter(User.email == request.email).first()
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")

    user = User(
        email=request.email,
        hashed_password=hash_password(request.password),
        role=request.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("")
def list_users(actor=Depends(require_admin), db: Session = Depends(get_db)):
    users = db.query(User).order_by(User.created_at).all()
    return [UserOut(id=u.id, email=u.email, role=u.role).model_dump() for u in users]


@router.patch("/{user_id}", response_model=UserOut)
def update_role(
    user_id: str,
    request: RoleUpdate,
    actor: User = Depends(require_root),
    db: Session = Depends(get_db),
):
    """Role changes are exclusive to the root account."""
    if request.role not in ("admin", "user"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Role must be 'admin' or 'user'")

    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    if user.id == actor.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "You cannot change your own role")
    if user.role == "root":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "The root account cannot be modified")

    user.role = request.role
    db.commit()
    return user


@router.delete("/{user_id}", status_code=204)
def delete_user(
    user_id: str,
    actor: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    if user.id == actor.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "You cannot delete your own account")
    if not _can_manage(actor, user):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Only the root account can delete administrator accounts",
        )

    db.delete(user)
    db.commit()
