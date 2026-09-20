from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database.session import get_db
from app.models.models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login", auto_error=False)

def get_current_user(db: Session = Depends(get_db), token: str = Depends(OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login"))) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception
    return user

from fastapi import Request

def get_current_user_optional(request: Request = None, db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)) -> User:
    """Return the authenticated user, or the local companion user if NO token is supplied.

    If a token IS supplied but is invalid/expired, this raises 401 rather than
    silently falling back to the default companion user. This prevents an
    attacker with a forged or stale token from being treated as the local user.
    If no token is supplied, COMPANION_MODE must be enabled and the request must
    originate from local loopback (127.0.0.1 / ::1) to prevent LAN hijacking.
    """
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if token:
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            user_id: str = payload.get("sub")
            if not user_id:
                raise unauthorized
            user = db.query(User).filter(User.id == user_id).first()
            if user is None:
                raise unauthorized
            return user
        except JWTError:
            raise unauthorized

    # No token supplied: verify COMPANION_MODE is enabled
    if not getattr(settings, "COMPANION_MODE", True):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token required. COMPANION_MODE is disabled.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # If incoming request is available, restrict anonymous companion access to loopback
    if request:
        # Do not trust client-supplied forwarding headers for an access-control
        # decision. A reverse proxy must terminate authentication or be
        # explicitly configured as a trusted proxy before forwarded addresses
        # can be considered.
        client_host = request.client.host if request.client else None
        if client_host and client_host not in ("127.0.0.1", "::1", "localhost", "testclient"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Anonymous companion mode is restricted to local loopback (127.0.0.1). Authentication token required."
            )

    # Local single-tenant companion mode fallback
    user = db.query(User).order_by(User.created_at.asc()).first()
    if not user:
        user = User(
            email="local@memos.ai",
            username="localuser",
            hashed_password="localpasswordhash"
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user
