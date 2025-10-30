from fastapi import Depends, HTTPException, status, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from uuid import UUID
from typing import Optional
import os

from fastapi_limiter.depends import RateLimiter

from app.database import get_db
from app.core.security import decode_access_token
from app.crud import user as user_crud
from app.models import User
from app.core.queue import BaseTaskQueueService, RedisTaskQueueService  
from app.core.storage import StorageService, LocalStorage, S3Storage

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


def get_current_user_from_query(
    token: str = Query(..., description="JWT token for authentication"),
    db: Session = Depends(get_db)
) -> User:
    """Get current user from query parameter token (for SSE)"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )
    
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


strict_rate_limiter = RateLimiter(times=20, seconds=300)
moderate_rate_limiter = RateLimiter(times=50, seconds=300)


def get_strict_rate_limiter():
    return Depends(strict_rate_limiter)

def get_moderate_rate_limiter():
    return Depends(moderate_rate_limiter)


_queue_service: BaseTaskQueueService = None  # Type hint to base class


async def get_queue_service() -> BaseTaskQueueService:  # Return base class
    """
    Returns task queue service. 
    Implementation can be switched via QUEUE_IMPL env var.
    Supported: redis (default), sqs
    """
    global _queue_service
    
    if _queue_service is None:
        queue_impl = os.getenv("QUEUE_IMPL", "redis").lower()
        
        if queue_impl == "redis":
            _queue_service = RedisTaskQueueService()
        # elif queue_impl == "sqs":
        #     _queue_service = SQSTaskQueueService(...)
        else:
            raise ValueError(f"Unsupported queue implementation: {queue_impl}")
    
    return _queue_service



_storage_service: StorageService = None  # Type hint to base class

async def get_storage_service(storage_type: Optional[str] = None) -> StorageService:
    global _storage_service
    if storage_type is None:
        storage_type = os.getenv("STORAGE_TYPE", "local").lower()
    
    if _storage_service is None:        
        if storage_type == "local":
            _storage_service = LocalStorage()
        elif storage_type == "s3":
            _storage_service = S3Storage()
        else:
            raise ValueError(f"Unsupported storage type: {storage_type}")
    
    return _storage_service


async def get_s3_storage_service() -> StorageService:
    """Get S3 storage service"""
    return await get_storage_service(storage_type="s3")
