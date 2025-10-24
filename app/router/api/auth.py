from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import timedelta

from app.database import get_db
from app.schemas import UserCreate, User, UserLogin, TokenResponse
from app.crud import user as user_crud
from app.core.security import (
    verify_password, 
    get_password_hash, 
    create_access_token,
    ACCESS_TOKEN_EXPIRE_MINUTES
)
from app.core.dependencies import get_current_user, get_strict_rate_limiter, get_moderate_rate_limiter


router = APIRouter(prefix="/auth", tags=["auth"])

from app.logger_config import get_logger
logger = get_logger(__name__)

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED, dependencies=[get_strict_rate_limiter()])
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    logger.info(f"Registration attempt for email: {user_in.email}")
    
    existing_user = user_crud.get_user_by_email(db, user_in.email)
    if existing_user:
        logger.warning(f"Email already registered: {user_in.email}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    password_hash = get_password_hash(user_in.password)
    user = user_crud.create_user(db, user_in, password_hash)
    logger.info(f"User successfully created: {user.email} (ID: {user.id})")
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=access_token_expires
    )
    
    return TokenResponse(access_token=access_token)


@router.post("/login", response_model=TokenResponse, dependencies=[get_strict_rate_limiter()])
def login(user_login: UserLogin, db: Session = Depends(get_db)):
    logger.info(f"Login attempt for email: {user_login.email}")
    
    user = user_crud.get_user_by_email(db, user_login.email)
    if not user:
        logger.warning(f"Login failed: user not found for email {user_login.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not verify_password(user_login.password, user.password_hash):
        logger.warning(f"Login failed: incorrect password for email {user_login.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_crud.update_last_login(db, user.id)
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=access_token_expires
    )
    
    logger.info(f"Login successful for user: {user.email} (ID: {user.id})")
    return TokenResponse(access_token=access_token)


@router.get("/me", response_model=User, dependencies=[get_moderate_rate_limiter()])
def get_current_user_info(current_user: User = Depends(get_current_user)):
    return current_user

