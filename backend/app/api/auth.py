from fastapi import APIRouter, Depends, HTTPException, Request, status
from collections import defaultdict
from threading import Lock
import time
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models.models import User
from app.schemas.schemas import UserCreate, UserLogin, UserResponse, Token
from app.core.security import verify_password, get_password_hash, create_access_token
from app.api.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])

_login_attempts = defaultdict(list)
_login_attempts_lock = Lock()
_LOGIN_WINDOW_SECONDS = 60
_LOGIN_MAX_ATTEMPTS = 5


def _check_login_rate_limit(key: str) -> None:
    # 1. Multi-worker Redis rate limiter when Redis is available
    try:
        from app.services.cache_service import cache_service
        r = cache_service._redis()
        if r is not None:
            now_epoch = int(time.time())
            window_bucket = now_epoch // _LOGIN_WINDOW_SECONDS
            redis_key = f"login_attempts:{key}:{window_bucket}"
            pipe = r.pipeline()
            pipe.incr(redis_key)
            pipe.expire(redis_key, _LOGIN_WINDOW_SECONDS * 2)
            results = pipe.execute()
            if results and int(results[0]) > _LOGIN_MAX_ATTEMPTS:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many login attempts. Try again later.",
                    headers={"Retry-After": str(_LOGIN_WINDOW_SECONDS)},
                )
            return
    except HTTPException:
        raise
    except Exception:
        pass

    # 2. Local thread-safe rate limiter fallback
    now = time.monotonic()
    with _login_attempts_lock:
        recent = [timestamp for timestamp in _login_attempts[key] if now - timestamp < _LOGIN_WINDOW_SECONDS]
        if len(recent) >= _LOGIN_MAX_ATTEMPTS:
            retry_after = max(1, int(_LOGIN_WINDOW_SECONDS - (now - recent[0])))
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many login attempts. Try again later.",
                headers={"Retry-After": str(retry_after)},
            )
        recent.append(now)
        _login_attempts[key] = recent

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    existing_email = db.query(User).filter(User.email == user_in.email).first()
    if existing_email:
        raise HTTPException(status_code=400, detail="Email is already registered")
    
    existing_username = db.query(User).filter(User.username == user_in.username).first()
    if existing_username:
        raise HTTPException(status_code=400, detail="Username is already taken")

    user = User(
        email=user_in.email,
        username=user_in.username,
        hashed_password=get_password_hash(user_in.password)
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@router.post("/login", response_model=Token)
def login(credentials: UserLogin, request: Request, db: Session = Depends(get_db)):
    client_host = request.client.host if request.client else "unknown"
    _check_login_rate_limit(f"{client_host}:{credentials.email.lower()}")
    user = db.query(User).filter(User.email == credentials.email).first()
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    access_token = create_access_token(subject=user.id)
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user
    }

@router.get("/profile", response_model=UserResponse)
def get_profile(current_user: User = Depends(get_current_user)):
    return current_user
