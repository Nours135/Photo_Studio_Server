from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from uuid import UUID

from fastapi_limiter.depends import RateLimiter

from app.database import get_db
from app.core.security import decode_access_token
from app.crud import user as user_crud
from app.models import User

security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    token = credentials.credentials
    payload = decode_access_token(token)
    
    if payload is None:
        raise credentials_exception
    
    user_id: str = payload.get("sub")
    if user_id is None:
        raise credentials_exception
    
    try:
        user = user_crud.get_user(db, UUID(user_id))
    except ValueError:
        raise credentials_exception
    
    if user is None:
        raise credentials_exception
    
    return user


strict_rate_limiter = RateLimiter(times=5, seconds=300)
moderate_rate_limiter = RateLimiter(times=10, seconds=600)


def get_strict_rate_limiter():
    return Depends(strict_rate_limiter)

def get_moderate_rate_limiter():
    return Depends(moderate_rate_limiter)