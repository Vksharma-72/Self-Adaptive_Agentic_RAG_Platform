from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.auth.security import decode_token
from app.db.database import get_db
from app.db.models import User


bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    payload = decode_token(credentials.credentials)
    if payload is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")

    user = db.get(User, payload.get("sub"))
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User no longer exists")
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    """Admins and root can manage the platform; root is the super-admin."""
    if user.role not in ("admin", "root"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin privileges required")
    return user


def require_root(user: User = Depends(get_current_user)) -> User:
    """Only the root account may grant/revoke admin privileges."""
    if user.role != "root":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the root account can do this")
    return user
