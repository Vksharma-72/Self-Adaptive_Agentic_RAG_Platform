import logfire
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.security import create_access_token, hash_password, verify_password
from app.config import settings
from app.db.database import get_db
from app.db.models import User


router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    email: str


class UserOut(BaseModel):
    id: str
    email: str
    role: str


@router.post("/register", response_model=UserOut, status_code=201)
def register(request: RegisterRequest, db: Session = Depends(get_db)):
    """Open registration — always creates a regular user.
    Admins are created by the root account (or seeded from env)."""
    if len(request.password) < 8:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Password must be at least 8 characters")

    existing = db.query(User).filter(User.email == request.email).first()
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")

    user = User(email=request.email, hashed_password=hash_password(request.password), role="user")
    db.add(user)
    db.commit()
    db.refresh(user)
    logfire.info(f"New user registered: {user.email}")
    return user


@router.post("/login", response_model=TokenResponse)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form.username).first()
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password")
    return TokenResponse(
        access_token=create_access_token(user.id, user.role),
        role=user.role,
        email=user.email,
    )


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


def seed_admin() -> None:
    """Create the bootstrap ROOT account from env vars if it doesn't exist.
    The root is the super-admin: the only account that can create admins."""
    if not settings.ADMIN_EMAIL or not settings.ADMIN_PASSWORD:
        logfire.warning("ADMIN_EMAIL/ADMIN_PASSWORD not set — no root account seeded.")
        return

    from app.db.database import SessionLocal

    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == settings.ADMIN_EMAIL).first()
        if existing:
            if existing.role != "root":
                existing.role = "root"
                db.commit()
                logfire.info(f"Existing account promoted to root: {settings.ADMIN_EMAIL}")
            return
        root = User(
            email=settings.ADMIN_EMAIL,
            hashed_password=hash_password(settings.ADMIN_PASSWORD),
            role="root",
        )
        db.add(root)
        db.commit()
        logfire.info(f"Root account seeded: {settings.ADMIN_EMAIL}")
    finally:
        db.close()
