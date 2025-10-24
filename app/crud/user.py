from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from uuid import UUID
from datetime import datetime

from app.models import User, SubscriptionTier
from app.schemas import UserCreate


def get_user(db: Session, user_id: UUID) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email).first()


def create_user(db: Session, user: UserCreate, password_hash: str) -> User:
    db_user = User(
        email=user.email,
        username=user.username,
        password_hash=password_hash,
        subscription_tier=SubscriptionTier.FREE
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def update_last_login(db: Session, user_id: UUID) -> Optional[User]:
    db_user = get_user(db, user_id)
    if not db_user:
        return None
    
    db_user.last_login = datetime.utcnow()
    db.commit()
    db.refresh(db_user)
    return db_user
